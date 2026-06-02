from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import json
import asyncio
from typing import Optional
from app.db import get_db
from app.models import Flag, Market
from app.schemas import FlagCreate, FlagUpdate, FlagResponse, FlagImportRequest, FlagImportResponse, ImportAllFlagsRequest, ImportAllFlagsResponse, UpdateFlagValueRequest, UpdateFlagValueResponse, RuleCreate, RuleUpdate, RuleResponse, RuleListResponse, RuleOperationResponse
from app.services.growthbook_client import GrowthBookClient, GROWTHBOOK_PROJECT_ID
from app.services.growthbook_error import GrowthBookError
from app.services.rule_validator import RuleValidator
from app.services.condition_parser import ConditionParser

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flags", tags=["flags"])


@router.get("", response_model=list[FlagResponse])
async def get_flags(market_id: Optional[int] = Query(None), environment: str = Query("dev"), search: Optional[str] = Query(None), db: AsyncSession = Depends(get_db)):
    try:
        query = select(Flag)
        
        if market_id:
            query = query.where(Flag.market_id == market_id)
        
        # Check if search is a condition (contains operators like =, :, >, <, etc.)
        is_condition_search = search and any(op in search for op in ['=', ':', '>', '<', '>=', '<=', '!='])
        
        # Add search filter for key/name (only if not a condition search)
        if search and not is_condition_search:
            search_pattern = f"%{search}%"
            query = query.where(Flag.key.ilike(search_pattern))
        
        result = await db.execute(query)
        flags = result.scalars().all()
        
        # Fetch rule data from GrowthBook for each flag using parallel calls
        # This improves performance from sequential (~4s) to parallel (~1s)
        gb_client = GrowthBookClient()
        flags_with_rules = []
        
        async def fetch_flag_data(flag):
            try:
                # Get feature from GrowthBook
                feature_response = await gb_client.get_feature(flag.growthbook_feature_id)
                feature = feature_response.get("feature", feature_response)
                
                # Extract rules from top-level of feature (GrowthBook stores rules at feature level)
                rules = feature.get("rules", [])
                
                flag_dict = {
                    "id": flag.id,
                    "key": flag.key,
                    "market_id": flag.market_id,
                    "growthbook_feature_id": flag.growthbook_feature_id,
                    "created_at": flag.created_at,
                    "updated_at": flag.updated_at,
                    "rule_count": len(rules),
                    "rules": rules
                }
                return flag_dict
            except GrowthBookError as e:
                # If GrowthBook fetch fails, include flag with rule_count = 0
                logger.warning(f"Failed to fetch rules for flag {flag.growthbook_feature_id}: {e}")
                return {
                    "id": flag.id,
                    "key": flag.key,
                    "market_id": flag.market_id,
                    "growthbook_feature_id": flag.growthbook_feature_id,
                    "created_at": flag.created_at,
                    "updated_at": flag.updated_at,
                    "rule_count": 0,
                    "rules": []
                }
        
        # Fetch all flags in parallel
        flag_tasks = [fetch_flag_data(flag) for flag in flags]
        flags_with_rules = await asyncio.gather(*flag_tasks)
        
        # Apply condition filtering if search is a condition
        if is_condition_search:
            flags_with_rules = ConditionParser.filter_flags_by_condition(flags_with_rules, search)
        
        return flags_with_rules
    except Exception as e:
        logger.error(f"Error fetching flags: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("", response_model=FlagResponse, status_code=201)
async def create_flag(flag: FlagCreate, db: AsyncSession = Depends(get_db)):
    """
    Create a new flag. Creates the feature in GrowthBook first, then saves a local reference.
    """
    try:
        # Fetch market to get environment flow
        market_result = await db.execute(select(Market).where(Market.id == flag.market_id))
        market = market_result.scalar_one_or_none()
        
        if not market:
            raise HTTPException(status_code=404, detail=f"Market with id {flag.market_id} not found")
        
        # Parse environment flow (e.g., "dev->qa->uat->production")
        environments_list = [env.strip() for env in market.env_flow.split("->")]
        logger.info(f"Market {market.name} environment flow: {environments_list}")
        
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Create feature in GrowthBook first
        logger.info(f"Creating feature in GrowthBook with key: {flag.key}")
        
        # Generate a feature ID for GrowthBook (using the key as the ID)
        feature_id = flag.key
        
        # Build environments config - enable only first env (dev), disable others
        environments_config = {}
        for idx, env in enumerate(environments_list):
            environments_config[env] = {
                "enabled": idx == 0,  # Only first environment is enabled
                "defaultValue": flag.default_value if flag.default_value else "false",
                "rules": []
            }
        
        gb_feature_data = {
            "id": feature_id,
            "description": flag.description if flag.description else "",
            "defaultValue": flag.default_value if flag.default_value else "false",
            "valueType": "boolean",  # Default to boolean type
            "owner": "admin",  # Default owner - could be configurable
            "environments": environments_config
        }
        
        # Add project ID if configured
        if GROWTHBOOK_PROJECT_ID:
            gb_feature_data["project"] = GROWTHBOOK_PROJECT_ID
            logger.info(f"Using project ID: {GROWTHBOOK_PROJECT_ID}")
        
        logger.info(f"GrowthBook feature data: {gb_feature_data}")
        
        try:
            gb_response = await gb_client.create_feature(gb_feature_data)
            logger.info(f"GrowthBook response: {gb_response}")
        except GrowthBookError as e:
            logger.error(f"GrowthBook error details: {e.response_data}")
            raise
        
        # Extract feature from response (GrowthBook wraps it in a "feature" key)
        feature = gb_response.get("feature") if isinstance(gb_response, dict) else gb_response
        gb_feature_id = feature.get("id") if isinstance(feature, dict) else feature.get("id")
        
        if not gb_feature_id:
            raise HTTPException(status_code=500, detail="Failed to get feature ID from GrowthBook")
        
        logger.info(f"Created feature in GrowthBook with ID: {gb_feature_id}")
        
        # Check if flag already exists for this market
        result = await db.execute(
            select(Flag).where(Flag.key == flag.key, Flag.market_id == flag.market_id)
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            logger.warning(f"Flag already exists: {flag.key} for market_id={flag.market_id}")
            raise HTTPException(status_code=400, detail="Flag with this key already exists for this market")
        
        # Save local flag with GrowthBook feature ID
        new_flag = Flag(
            key=flag.key,
            market_id=flag.market_id,
            growthbook_feature_id=gb_feature_id
        )
        db.add(new_flag)
        await db.commit()
        await db.refresh(new_flag)
        
        logger.info(f"Created local flag with id={new_flag.id}")
        return new_flag
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create feature in GrowthBook: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating flag {flag.key}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{flag_id}", response_model=FlagResponse)
async def update_flag(flag_id: int, flag: FlagUpdate, db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(select(Flag).where(Flag.id == flag_id))
        db_flag = result.scalar_one_or_none()
        
        if not db_flag:
            logger.warning(f"Flag not found: {flag_id}")
            raise HTTPException(status_code=404, detail="Flag not found")
        
        update_data = flag.model_dump(exclude_unset=True)
        
        if not update_data:
            logger.warning(f"No fields to update for flag_id={flag_id}")
            raise HTTPException(status_code=400, detail="No fields to update")
        
        from sqlalchemy.sql import func
        for field, value in update_data.items():
            setattr(db_flag, field, value)
        
        # Manually update the updated_at timestamp
        db_flag.updated_at = func.now()
        
        await db.commit()
        await db.refresh(db_flag)
        
        logger.info(f"Updated flag: {flag_id}")
        return db_flag
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating flag {flag_id}: {e}")
        await db.rollback()
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/import", response_model=FlagImportResponse)
async def import_flag(request: FlagImportRequest, db: AsyncSession = Depends(get_db)):
    """
    Import a flag from GrowthBook by its feature ID.
    This will fetch the feature from GrowthBook and create a local flag.
    """
    try:
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Fetch feature from GrowthBook
        logger.info(f"Fetching feature {request.growthbook_feature_id} from GrowthBook")
        feature_data = await gb_client.get_feature(request.growthbook_feature_id)
        
        # Determine the key for the local flag
        flag_key = request.key if request.key else feature_data.get("key", request.growthbook_feature_id)
        
        # Check if flag already exists for this market
        existing_result = await db.execute(
            select(Flag).where(
                Flag.market_id == request.market_id,
                Flag.growthbook_feature_id == request.growthbook_feature_id
            )
        )
        existing_flag = existing_result.scalar_one_or_none()
        
        if existing_flag:
            # Update existing flag
            existing_flag.key = flag_key
            await db.commit()
            await db.refresh(existing_flag)
            logger.info(f"Updated existing flag with id={existing_flag.id}")
            return FlagImportResponse(
                success=True,
                message="Flag updated successfully",
                flag=existing_flag
            )
        
        # Create new flag
        new_flag = Flag(
            key=flag_key,
            market_id=request.market_id,
            growthbook_feature_id=request.growthbook_feature_id
        )
        db.add(new_flag)
        await db.commit()
        await db.refresh(new_flag)
        logger.info(f"Created new flag with id={new_flag.id}")
        
        return FlagImportResponse(
            success=True,
            message="Flag imported successfully",
            flag=new_flag
        )
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        return FlagImportResponse(
            success=False,
            message=f"Failed to fetch feature from GrowthBook: {e.message}",
            error=str(e)
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return FlagImportResponse(
            success=False,
            message=f"GrowthBook configuration error: {str(e)}",
            error=str(e)
        )
    except Exception as e:
        logger.error(f"Error importing flag: {e}")
        return FlagImportResponse(
            success=False,
            message=f"Unexpected error: {str(e)}",
            error=str(e)
        )


@router.get("/{flag_id}/gb-details")
async def get_flag_gb_details(flag_id: int, environment: str = Query("dev"), db: AsyncSession = Depends(get_db)):
    """
    Get flag details from GrowthBook including environment-specific values and rules.
    """
    try:
        # Get the flag from the database
        result = await db.execute(select(Flag).where(Flag.id == flag_id))
        db_flag = result.scalar_one_or_none()
        
        if not db_flag:
            logger.warning(f"Flag not found: {flag_id}")
            raise HTTPException(status_code=404, detail="Flag not found")
        
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Fetch feature from GrowthBook
        logger.info(f"Fetching feature {db_flag.growthbook_feature_id} from GrowthBook")
        feature_response = await gb_client.get_feature(db_flag.growthbook_feature_id)
        feature = feature_response.get("feature", feature_response)
        
        # Extract rules from top-level of feature
        all_rules = feature.get("rules", [])
        logger.info(f"Total rules for flag {db_flag.growthbook_feature_id}: {len(all_rules)}")
        
        # Filter rules for the specified environment
        environment_rules = []
        for rule in all_rules:
            rule_envs = rule.get("environments", [])
            if not rule_envs or environment in rule_envs or rule.get("allEnvironments", False):
                environment_rules.append(rule)
        
        logger.info(f"Environment-specific rules for {environment}: {len(environment_rules)}")
        
        # Extract environment data
        env_data = {}
        if "environments" in feature and environment in feature["environments"]:
            env_data = feature["environments"][environment]
        
        return {
            "success": True,
            "flag": {
                "id": db_flag.id,
                "key": db_flag.key,
                "growthbook_feature_id": db_flag.growthbook_feature_id,
                "market_id": db_flag.market_id
            },
            "environments": feature.get("environments", {}),
            "defaultValue": feature.get("defaultValue", "false"),
            "valueType": feature.get("valueType", "boolean"),
            "environment": environment,
            "enabled": env_data.get("enabled", False),
            "default_value": env_data.get("defaultValue", "false"),
            "rules": environment_rules,
            "rule_count": len(environment_rules)
        }
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch feature from GrowthBook: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching flag details {flag_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/{flag_id}/update-gb-value", response_model=UpdateFlagValueResponse)
async def update_flag_gb_value(flag_id: int, request: UpdateFlagValueRequest, db: AsyncSession = Depends(get_db)):
    """
    Update a flag's value in GrowthBook for a specific environment.
    """
    try:
        # Get the flag from the database
        result = await db.execute(select(Flag).where(Flag.id == flag_id))
        db_flag = result.scalar_one_or_none()
        
        if not db_flag:
            logger.warning(f"Flag not found: {flag_id}")
            raise HTTPException(status_code=404, detail="Flag not found")
        
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Update the flag value in GrowthBook for the specific environment
        logger.info(f"Updating flag {db_flag.growthbook_feature_id} in environment {request.environment}")
        response = await gb_client.update_feature_environment(
            feature_id=db_flag.growthbook_feature_id,
            environment=request.environment,
            enabled=request.enabled,
            default_value=request.default_value
        )
        
        logger.info(f"Successfully updated flag {db_flag.growthbook_feature_id} in environment {request.environment}")
        
        return UpdateFlagValueResponse(
            success=True,
            message=f"Successfully updated flag in environment {request.environment}"
        )
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        return UpdateFlagValueResponse(
            success=False,
            message=f"Failed to update flag in GrowthBook: {e.message}",
            error=str(e)
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating flag {flag_id}: {e}")
        return UpdateFlagValueResponse(
            success=False,
            message=f"Unexpected error: {str(e)}",
            error=str(e)
        )


@router.post("/{flag_id}/archive")
async def archive_flag(flag_id: int, db: AsyncSession = Depends(get_db)):
    """
    Archive a flag in GrowthBook.
    """
    try:
        # Get the flag from the database
        result = await db.execute(select(Flag).where(Flag.id == flag_id))
        db_flag = result.scalar_one_or_none()
        
        if not db_flag:
            logger.warning(f"Flag not found: {flag_id}")
            raise HTTPException(status_code=404, detail="Flag not found")
        
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Archive the flag in GrowthBook
        logger.info(f"Archiving flag {db_flag.growthbook_feature_id} in GrowthBook")
        response = await gb_client.archive_feature(db_flag.growthbook_feature_id)
        
        logger.info(f"Successfully archived flag {db_flag.growthbook_feature_id}")
        
        return {
            "success": True,
            "message": "Flag archived successfully in GrowthBook"
        }
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to archive flag in GrowthBook: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving flag {flag_id}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.post("/import-all", response_model=ImportAllFlagsResponse)
async def import_all_flags(request: ImportAllFlagsRequest, db: AsyncSession = Depends(get_db)):
    """
    Import all flags from GrowthBook for a specific market.
    Uses the configured GROWTHBOOK_PROJECT_ID from environment if set.
    With dry_run=True, returns sync plan without executing changes.
    """
    try:
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Fetch all features from GrowthBook (filtered by configured project if set)
        logger.info(f"Fetching all features from GrowthBook for market_id={request.market_id}")
        response = await gb_client.get_all_features()
        
        # Extract features from response
        features = response.get("features", []) if isinstance(response, dict) else []
        if not features and isinstance(response, list):
            features = response
        
        logger.info(f"Received {len(features)} features from GrowthBook")
        if features:
            feature_ids = [f.get("id") for f in features if f.get("id")]
            logger.info(f"Feature IDs from GrowthBook: {feature_ids}")
        
        # Get all local flags for this market
        local_result = await db.execute(
            select(Flag).where(Flag.market_id == request.market_id)
        )
        local_flags = local_result.scalars().all()
        local_feature_ids = {flag.growthbook_feature_id for flag in local_flags}
        
        logger.info(f"Found {len(local_flags)} local flags for market_id={request.market_id}")
        
        # Categorize sync operations
        to_add = []
        to_update = []
        to_delete = []
        
        imported_count = 0
        updated_count = 0
        deleted_count = 0
        failed_count = 0
        imported_flags = []
        errors = []
        
        for feature in features:
            try:
                feature_id = feature.get("id")
                feature_key = feature.get("key", feature_id)
                archived = feature.get("archived", False)
                
                if not feature_id:
                    errors.append(f"Feature missing ID: {feature}")
                    failed_count += 1
                    continue
                
                # Skip archived flags
                if archived:
                    logger.info(f"Skipping archived feature: {feature_id}")
                    continue
                
                if feature_id in local_feature_ids:
                    # Flag exists locally - mark for update
                    to_update.append({
                        "key": feature_key,
                        "growthbook_feature_id": feature_id
                    })
                else:
                    # Flag doesn't exist locally - mark for add
                    to_add.append({
                        "key": feature_key,
                        "growthbook_feature_id": feature_id
                    })
            except Exception as e:
                errors.append(f"Error processing feature {feature.get('id', 'unknown')}: {str(e)}")
                failed_count += 1
        
        # Find local flags not in GrowthBook - mark for delete
        gb_feature_ids = {f.get("id") for f in features if f.get("id") and not f.get("archived", False)}
        for local_flag in local_flags:
            if local_flag.growthbook_feature_id not in gb_feature_ids:
                to_delete.append({
                    "key": local_flag.key,
                    "growthbook_feature_id": local_flag.growthbook_feature_id
                })
        
        logger.info(
            f"Sync plan: {len(to_add)} to add, {len(to_update)} to update, {len(to_delete)} to delete"
        )
        
        # If dry_run, return the plan without executing
        if request.dry_run:
            return ImportAllFlagsResponse(
                success=True,
                message="Dry run completed successfully",
                imported_count=0,
                updated_count=0,
                deleted_count=0,
                failed_count=0,
                flags=[],
                errors=errors,
                to_add=to_add,
                to_update=to_update,
                to_delete=to_delete,
                dry_run=True
            )
        
        # Execute sync operations
        # Process adds
        for feature in features:
            try:
                feature_id = feature.get("id")
                feature_key = feature.get("key", feature_id)
                archived = feature.get("archived", False)
                
                if not feature_id or archived:
                    continue
                
                # Check if flag already exists for this market
                existing_result = await db.execute(
                    select(Flag).where(
                        Flag.market_id == request.market_id,
                        Flag.growthbook_feature_id == feature_id
                    )
                )
                existing_flag = existing_result.scalar_one_or_none()
                
                if existing_flag:
                    # Update existing flag
                    existing_flag.key = feature_key
                    await db.commit()
                    await db.refresh(existing_flag)
                    imported_flags.append(existing_flag)
                    updated_count += 1
                    logger.info(f"Updated existing flag with id={existing_flag.id}")
                else:
                    # Create new flag
                    new_flag = Flag(
                        key=feature_key,
                        market_id=request.market_id,
                        growthbook_feature_id=feature_id
                    )
                    db.add(new_flag)
                    await db.commit()
                    await db.refresh(new_flag)
                    imported_flags.append(new_flag)
                    imported_count += 1
                    logger.info(f"Created new flag with id={new_flag.id}")
            
            except Exception as e:
                error_msg = f"Failed to import feature {feature.get('id', 'unknown')}: {str(e)}"
                errors.append(error_msg)
                failed_count += 1
                logger.error(error_msg)
                await db.rollback()
        
        # Process deletes
        for delete_item in to_delete:
            try:
                feature_id = delete_item["growthbook_feature_id"]
                delete_result = await db.execute(
                    select(Flag).where(
                        Flag.market_id == request.market_id,
                        Flag.growthbook_feature_id == feature_id
                    )
                )
                flag_to_delete = delete_result.scalar_one_or_none()
                
                if flag_to_delete:
                    await db.delete(flag_to_delete)
                    await db.commit()
                    deleted_count += 1
                    logger.info(f"Deleted flag with id={flag_to_delete.id}")
            except Exception as e:
                errors.append(f"Error deleting flag {delete_item['key']}: {str(e)}")
                failed_count += 1
                await db.rollback()
        
        logger.info(
            f"Sync completed: {imported_count} added, {updated_count} updated, {deleted_count} deleted"
        )
        
        return ImportAllFlagsResponse(
            success=True,
            message=f"Sync completed: {imported_count} added, {updated_count} updated, {deleted_count} deleted",
            imported_count=imported_count,
            updated_count=updated_count,
            deleted_count=deleted_count,
            failed_count=failed_count,
            flags=imported_flags,
            errors=errors,
            to_add=to_add,
            to_update=to_update,
            to_delete=to_delete,
            dry_run=False
        )
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        return ImportAllFlagsResponse(
            success=False,
            message=f"Failed to fetch features from GrowthBook: {e.message}",
            errors=[str(e)],
            dry_run=request.dry_run
        )
    except ValueError as e:
        logger.error(f"Configuration error: {e}")
        return ImportAllFlagsResponse(
            success=False,
            message=f"GrowthBook configuration error: {str(e)}",
            errors=[str(e)],
            dry_run=request.dry_run
        )
    except Exception as e:
        logger.error(f"Error importing flags: {e}")
        return ImportAllFlagsResponse(
            success=False,
            message=f"Unexpected error: {str(e)}",
            errors=[str(e)],
            dry_run=request.dry_run
        )


# Rule Management Endpoints (POC - Phase 1)

@router.post("/{flag_id}/rules")
async def add_rule(flag_id: int, rule_data: dict, environment: str = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Add a rule to a flag in a specific environment.
    Validates rule structure before sending to GrowthBook.
    """
    try:
        # Validate rule structure
        is_valid, error = RuleValidator.validate_rule(rule_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid rule: {error}")
        
        # Get the flag from database
        result = await db.execute(select(Flag).where(Flag.id == flag_id))
        db_flag = result.scalar_one_or_none()
        
        if not db_flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Add rule to GrowthBook
        logger.info(f"Adding rule to flag {db_flag.growthbook_feature_id} in environment {environment}")
        response = await gb_client.add_rule(db_flag.growthbook_feature_id, environment, rule_data)
        
        return {
            "success": True,
            "message": "Rule added successfully",
            "data": response
        }
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to add rule: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error adding rule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{flag_id}/rules")
async def update_rules(flag_id: int, rules_data: dict, environment: str = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Update all rules for a flag in a specific environment.
    Replaces existing rules with the new set of rules.
    """
    try:
        rules = rules_data.get("rules", [])
        logger.info(f"Updating {len(rules)} rules for flag {flag_id} in environment {environment}")
        
        # Validate all rules
        for i, rule in enumerate(rules):
            is_valid, error = RuleValidator.validate_rule(rule)
            if not is_valid:
                raise HTTPException(status_code=400, detail=f"Invalid rule at index {i}: {error}")
        
        # Get the flag from database
        result = await db.execute(select(Flag).where(Flag.id == flag_id))
        db_flag = result.scalar_one_or_none()
        
        if not db_flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Get current feature from GrowthBook
        current_feature = await gb_client._request("GET", f"/v2/features/{db_flag.growthbook_feature_id}")
        
        # Extract the feature data from the response (GrowthBook wraps it in a "feature" key)
        if "feature" in current_feature:
            current_feature = current_feature["feature"]
        
        # Ensure environment exists
        if "environments" not in current_feature:
            current_feature["environments"] = {}
        if environment not in current_feature["environments"]:
            current_feature["environments"][environment] = {}
        
        # Update rules for the environment
        # According to GrowthBook API docs, rules should be in the global rules array
        # with an "environments" array to specify which environments they apply to
        current_feature["rules"] = rules
        
        # Ensure environment exists and is enabled
        if "environments" not in current_feature:
            current_feature["environments"] = {}
        if environment not in current_feature["environments"]:
            current_feature["environments"][environment] = {}
        if "definition" in current_feature["environments"][environment]:
            del current_feature["environments"][environment]["definition"]
        
        # Filter the payload to only include editable fields that GrowthBook accepts
        # Remove read-only metadata fields that cause API errors
        update_payload = {
            "description": current_feature.get("description", ""),
            "defaultValue": current_feature.get("defaultValue"),
            "environments": current_feature.get("environments", {}),
            "rules": current_feature.get("rules", []),
            "prerequisites": current_feature.get("prerequisites", []),
            "tags": current_feature.get("tags", []),
            "customFields": current_feature.get("customFields", {})
        }
        
        # Update feature in GrowthBook
        logger.info(f"Updating feature {db_flag.growthbook_feature_id} with new rules for environment {environment}")
        response = await gb_client._request("POST", f"/v2/features/{db_flag.growthbook_feature_id}", update_payload)
        logger.info(f"Rules updated successfully")
        
        return {
            "success": True,
            "message": f"Updated {len(rules)} rules successfully",
            "data": response
        }
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update rules: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rules: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.put("/{flag_id}/rules/{rule_index}")
async def update_rule(flag_id: int, rule_index: int, rule_data: dict, environment: str = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Update an existing rule in a flag's environment.
    Validates rule structure before sending to GrowthBook.
    """
    try:
        # Validate rule structure
        is_valid, error = RuleValidator.validate_rule(rule_data)
        if not is_valid:
            raise HTTPException(status_code=400, detail=f"Invalid rule: {error}")
        
        # Get the flag from database
        result = await db.execute(select(Flag).where(Flag.id == flag_id))
        db_flag = result.scalar_one_or_none()
        
        if not db_flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Update rule in GrowthBook
        logger.info(f"Updating rule {rule_index} in flag {db_flag.growthbook_feature_id} environment {environment}")
        response = await gb_client.update_rule(db_flag.growthbook_feature_id, environment, rule_index, rule_data)
        
        return {
            "success": True,
            "message": "Rule updated successfully",
            "data": response
        }
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update rule: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating rule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.delete("/{flag_id}/rules/{rule_index}")
async def delete_rule(flag_id: int, rule_index: int, environment: str = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Delete a rule from a flag's environment.
    """
    try:
        # Get the flag from database
        result = await db.execute(select(Flag).where(Flag.id == flag_id))
        db_flag = result.scalar_one_or_none()
        
        if not db_flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Delete rule from GrowthBook
        logger.info(f"Deleting rule {rule_index} from flag {db_flag.growthbook_feature_id} environment {environment}")
        response = await gb_client.delete_rule(db_flag.growthbook_feature_id, environment, rule_index)
        
        return {
            "success": True,
            "message": "Rule deleted successfully",
            "data": response
        }
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete rule: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting rule: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@router.get("/{flag_id}/rules")
async def get_rules(flag_id: int, environment: str = Query(...), db: AsyncSession = Depends(get_db)):
    """
    Get all rules for a flag in a specific environment.
    """
    try:
        # Get the flag from database
        result = await db.execute(select(Flag).where(Flag.id == flag_id))
        db_flag = result.scalar_one_or_none()
        
        if not db_flag:
            raise HTTPException(status_code=404, detail="Flag not found")
        
        # Initialize GrowthBook client
        gb_client = GrowthBookClient()
        
        # Get feature from GrowthBook
        feature = await gb_client.get_feature(db_flag.growthbook_feature_id)
        
        # Extract rules for the specified environment
        rules = []
        if "environments" in feature and environment in feature["environments"]:
            rules = feature["environments"][environment].get("rules", [])
        
        return {
            "success": True,
            "flag_id": flag_id,
            "environment": environment,
            "rules": rules,
            "count": len(rules)
        }
    
    except GrowthBookError as e:
        logger.error(f"GrowthBook API error: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get rules: {e.message}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting rules: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


