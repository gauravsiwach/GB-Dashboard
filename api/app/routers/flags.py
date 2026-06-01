from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
from typing import Optional
from app.db import get_db
from app.models import Flag, Market
from app.schemas import FlagCreate, FlagUpdate, FlagResponse, FlagImportRequest, FlagImportResponse, ImportAllFlagsRequest, ImportAllFlagsResponse, UpdateFlagValueRequest, UpdateFlagValueResponse
from app.services.growthbook_client import GrowthBookClient, GROWTHBOOK_PROJECT_ID
from app.services.growthbook_error import GrowthBookError

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/flags", tags=["flags"])


@router.get("", response_model=list[FlagResponse])
async def get_flags(market_id: Optional[int] = Query(None), db: AsyncSession = Depends(get_db)):
    try:
        query = select(Flag)
        
        if market_id:
            query = query.where(Flag.market_id == market_id)
        
        result = await db.execute(query)
        flags = result.scalars().all()
        logger.info(f"Retrieved {len(flags)} flags for market_id={market_id}")
        return flags
    except Exception as e:
        logger.error(f"Error retrieving flags: {e}")
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
async def get_flag_gb_details(flag_id: int, db: AsyncSession = Depends(get_db)):
    """
    Get flag details from GrowthBook including environment-specific values.
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
        response = await gb_client.get_feature(db_flag.growthbook_feature_id)
        
        # Extract feature data
        feature_data = response.get("feature", response)
        
        return {
            "success": True,
            "flag": {
                "id": db_flag.id,
                "key": db_flag.key,
                "growthbook_feature_id": db_flag.growthbook_feature_id,
                "market_id": db_flag.market_id
            },
            "environments": feature_data.get("environments", {}),
            "defaultValue": feature_data.get("defaultValue", "false"),
            "valueType": feature_data.get("valueType", "boolean")
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
