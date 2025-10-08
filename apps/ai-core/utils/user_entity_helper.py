from typing import Optional
import logging

logger = logging.getLogger(__name__)


def get_or_create_user_entity(db, user_id: str = "default_user") -> Optional[str]:
    """
    Get or create a person entity for the user

    Args:
        db: DatabaseService instance
        user_id: User identifier (from auth system)

    Returns:
        Entity ID of the user's person entity, or None if creation fails
    """
    try:
        # Check if user entity already exists in metadata
        # Query for person entities with this user_id in metadata
        result = db.supabase.table('entity').select('id').eq('type', 'person').execute()

        if result.data:
            for entity in result.data:
                # Fetch full entity to check metadata
                full_entity = db.get_entity_by_id(entity['id'])
                if full_entity and full_entity.metadata.get('user_id') == user_id:
                    logger.info(f"Found existing user entity for {user_id}: {entity['id']}")
                    return entity['id']

        # If no existing entity, create one
        logger.info(f"Creating new user entity for {user_id}")

        entity_payload = {
            'type': 'person',
            'title': f'User ({user_id})',  # Will be updated when user provides their name
            'summary': 'User of the system',
            'metadata': {
                'user_id': user_id,
                'is_system_user': True,
                'created_via': 'auto_user_entity'
            },
            'source_event_id': None  # Not tied to a specific event
        }

        entity_id = db.create_entity(entity_payload)
        logger.info(f"Created user entity for {user_id}: {entity_id}")

        return entity_id

    except Exception as e:
        logger.error(f"Error getting/creating user entity: {e}")
        return None


def update_user_entity_from_introduction(
    db,
    user_entity_id: str,
    name: Optional[str] = None,
    metadata_updates: Optional[dict] = None
):
    """
    Update user entity when they introduce themselves

    Args:
        db: DatabaseService instance
        user_entity_id: The user's entity ID
        name: User's actual name (if extracted)
        metadata_updates: Additional metadata to merge
    """
    try:
        entity = db.get_entity_by_id(user_entity_id)

        if not entity:
            logger.warning(f"User entity {user_entity_id} not found")
            return

        updates = {}

        # Update title if name provided
        if name:
            updates['title'] = name
            logger.info(f"Updating user entity title to: {name}")

        # Merge metadata updates
        if metadata_updates:
            current_metadata = entity.metadata or {}
            current_metadata.update(metadata_updates)
            updates['metadata'] = current_metadata

        if updates:
            db.update_entity_metadata(user_entity_id, updates.get('metadata', entity.metadata))
            logger.info(f"Updated user entity {user_entity_id}")

    except Exception as e:
        logger.error(f"Error updating user entity: {e}")
