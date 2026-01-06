"""
External Content Service

Handles all external content library operations including CRUD operations,
S3 file management, and segments retrieval.
"""

import os
import uuid
import mimetypes
from datetime import datetime
from uuid import UUID
from typing import List, Dict, Any, Optional, Tuple
from sqlalchemy import or_

# Import database models and session
try:
    from scripts.db import DatabaseSession, ExternalContent, ExternalContentSegment
    from scripts.config_loader import get_config
except ImportError:
    from ..scripts.db import DatabaseSession, ExternalContent, ExternalContentSegment
    from ..scripts.config_loader import get_config

# Import S3 client
try:
    import boto3
except ImportError:
    boto3 = None


def get_s3_client():
    """Get configured S3 client."""
    config = get_config()
    return boto3.client(
        's3',
        aws_access_key_id=config.aws_access_key_id,
        aws_secret_access_key=config.aws_secret_access_key,
        region_name=config.aws_region
    )


class ExternalContentService:
    """Service for managing external content library operations."""

    @staticmethod
    def list_content(search_query: str = '', content_type: str = '', limit: int = 100) -> List[Dict[str, Any]]:
        """
        List external content with search and filters.

        Args:
            search_query: Search term for title, description, or author
            content_type: Filter by content type
            limit: Maximum number of items to return

        Returns:
            List of external content items with basic information
        """
        with DatabaseSession() as db_session:
            query = db_session.query(ExternalContent)

            # Apply search filter
            if search_query:
                search_term = f'%{search_query}%'
                query = query.filter(
                    or_(
                        ExternalContent.title.ilike(search_term),
                        ExternalContent.description.ilike(search_term),
                        ExternalContent.author.ilike(search_term)
                    )
                )

            # Apply content type filter
            if content_type:
                query = query.filter(ExternalContent.content_type == content_type)

            items = query.order_by(ExternalContent.created_at.desc()).limit(limit).all()

            return [{
                'id': str(item.id),
                'title': item.title,
                'content_type': item.content_type,
                'description': item.description,
                'source_url': item.source_url,
                'author': item.author,
                'content_date': item.content_date.isoformat() if item.content_date else None,
                'tags': item.tags or [],
                'word_count': item.word_count,
                'duration_seconds': float(item.duration_seconds) if item.duration_seconds else None,
                'status': item.status,
                'created_at': item.created_at.isoformat(),
                'created_by': str(item.created_by) if item.created_by else None
            } for item in items]

    @staticmethod
    def create_content(data: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Create new external content entry.

        Args:
            data: Content data including title, content_type, description, etc.
            user_id: ID of the user creating the content

        Returns:
            Dictionary with success status and created item ID

        Raises:
            ValueError: If required fields are missing
        """
        if not data.get('title') or not data.get('content_type'):
            raise ValueError('Title and content_type are required')

        with DatabaseSession() as db_session:
            item = ExternalContent(
                title=data['title'],
                content_type=data['content_type'],
                description=data.get('description', ''),
                source_url=data.get('source_url', ''),
                author=data.get('author', ''),
                content_date=datetime.strptime(data['content_date'], '%Y-%m-%d').date() if data.get('content_date') else None,
                tags=data.get('tags', []),
                extra_data=data.get('extra_data', {}),
                created_by=UUID(user_id) if user_id and user_id != 'demo-user-id' else None
            )
            db_session.add(item)
            db_session.commit()

            return {
                'success': True,
                'id': str(item.id),
                'message': f'{data["content_type"].title()} created successfully'
            }

    @staticmethod
    def get_content_with_urls(content_id: str) -> Dict[str, Any]:
        """
        Get single external content item with full details and S3 URLs.

        Args:
            content_id: UUID of the content item

        Returns:
            Complete content item with preview and download URLs

        Raises:
            ValueError: If content ID is invalid
            FileNotFoundError: If content is not found
        """
        try:
            content_uuid = UUID(content_id)
        except ValueError:
            raise ValueError('Invalid content ID')

        with DatabaseSession() as db_session:
            item = db_session.query(ExternalContent).filter(
                ExternalContent.id == content_uuid
            ).first()

            if not item:
                raise FileNotFoundError('Content not found')

            # Generate presigned URLs if S3 file exists
            preview_url = None
            download_url = None
            if item.s3_key:
                s3_client = get_s3_client()
                config = get_config()
                bucket = item.s3_bucket or config.s3_bucket

                # Preview URL (1 hour expiry)
                preview_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={'Bucket': bucket, 'Key': item.s3_key},
                    ExpiresIn=3600
                )

                # Download URL with original filename
                download_url = s3_client.generate_presigned_url(
                    'get_object',
                    Params={
                        'Bucket': bucket,
                        'Key': item.s3_key,
                        'ResponseContentDisposition': f'attachment; filename="{item.original_filename or item.title}"'
                    },
                    ExpiresIn=3600
                )

            # Get segments count
            segments_count = db_session.query(ExternalContentSegment).filter(
                ExternalContentSegment.content_id == item.id
            ).count()

            return {
                'id': str(item.id),
                'title': item.title,
                'content_type': item.content_type,
                'description': item.description,
                'source_url': item.source_url,
                'original_filename': item.original_filename,
                'file_size_bytes': item.file_size_bytes,
                'file_format': item.file_format,
                'content_text': item.content_text,
                'content_summary': item.content_summary,
                'word_count': item.word_count,
                'duration_seconds': float(item.duration_seconds) if item.duration_seconds else None,
                'author': item.author,
                'content_date': item.content_date.isoformat() if item.content_date else None,
                'tags': item.tags or [],
                'keywords': item.keywords or [],
                'extra_data': item.extra_data or {},
                'status': item.status,
                'processing_notes': item.processing_notes,
                'segments_count': segments_count,
                'preview_url': preview_url,
                'download_url': download_url,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat(),
                'created_by': str(item.created_by) if item.created_by else None
            }

    @staticmethod
    def update_content(content_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update external content metadata.

        Args:
            content_id: UUID of the content item
            data: Updated data fields

        Returns:
            Dictionary with success status

        Raises:
            ValueError: If content ID is invalid
            FileNotFoundError: If content is not found
        """
        try:
            content_uuid = UUID(content_id)
        except ValueError:
            raise ValueError('Invalid content ID')

        with DatabaseSession() as db_session:
            item = db_session.query(ExternalContent).filter(
                ExternalContent.id == content_uuid
            ).first()

            if not item:
                raise FileNotFoundError('Content not found')

            # Update fields if provided
            if 'title' in data:
                item.title = data['title']
            if 'description' in data:
                item.description = data['description']
            if 'author' in data:
                item.author = data['author']
            if 'content_date' in data and data['content_date']:
                item.content_date = datetime.strptime(data['content_date'], '%Y-%m-%d').date()
            if 'tags' in data:
                item.tags = data['tags']
            if 'status' in data:
                item.status = data['status']
            if 'processing_notes' in data:
                item.processing_notes = data['processing_notes']

            # Update extra_data with custom fields
            if 'extra_data' in data:
                extra = item.extra_data or {}
                extra.update(data['extra_data'])
                item.extra_data = extra

            item.updated_at = datetime.utcnow()
            db_session.commit()

            return {'success': True, 'message': 'Content updated successfully'}

    @staticmethod
    def delete_content(content_id: str) -> Dict[str, Any]:
        """
        Delete external content and associated files.

        Args:
            content_id: UUID of the content item

        Returns:
            Dictionary with success status

        Raises:
            ValueError: If content ID is invalid
            FileNotFoundError: If content is not found
        """
        try:
            content_uuid = UUID(content_id)
        except ValueError:
            raise ValueError('Invalid content ID')

        with DatabaseSession() as db_session:
            item = db_session.query(ExternalContent).filter(
                ExternalContent.id == content_uuid
            ).first()

            if not item:
                raise FileNotFoundError('Content not found')

            # Delete from S3 if file exists
            if item.s3_key:
                try:
                    s3_client = get_s3_client()
                    config = get_config()
                    bucket = item.s3_bucket or config.s3_bucket
                    s3_client.delete_object(Bucket=bucket, Key=item.s3_key)
                except Exception as e:
                    print(f"Error deleting S3 file {item.s3_key}: {e}")

            # Delete thumbnail if exists
            if item.thumbnail_s3_key:
                try:
                    s3_client = get_s3_client()
                    bucket = item.s3_bucket or config.s3_bucket
                    s3_client.delete_object(Bucket=bucket, Key=item.thumbnail_s3_key)
                except Exception as e:
                    print(f"Error deleting S3 thumbnail {item.thumbnail_s3_key}: {e}")

            # Delete from database (segments cascade automatically)
            db_session.delete(item)
            db_session.commit()

            return {'success': True, 'message': 'Content deleted successfully'}

    @staticmethod
    def get_content_segments(content_id: str) -> List[Dict[str, Any]]:
        """
        Get all segments for external content.

        Args:
            content_id: UUID of the content item

        Returns:
            List of content segments

        Raises:
            ValueError: If content ID is invalid
        """
        try:
            content_uuid = UUID(content_id)
        except ValueError:
            raise ValueError('Invalid content ID')

        with DatabaseSession() as db_session:
            segments = db_session.query(ExternalContentSegment).filter(
                ExternalContentSegment.content_id == content_uuid
            ).order_by(ExternalContentSegment.segment_index).all()

            return [{
                'id': str(seg.id),
                'segment_index': seg.segment_index,
                'section_title': seg.section_title,
                'start_time': float(seg.start_time) if seg.start_time else None,
                'end_time': float(seg.end_time) if seg.end_time else None,
                'start_position': seg.start_position,
                'end_position': seg.end_position,
                'text': seg.text,
                'speaker': seg.speaker,
                'confidence': float(seg.confidence) if seg.confidence else None,
                'created_at': seg.created_at.isoformat()
            } for seg in segments]

    @staticmethod
    def upload_file(file, metadata: Dict[str, Any], user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Upload external content file to S3 and create database record.

        Args:
            file: File object from request
            metadata: File metadata including title, content_type, description, author
            user_id: ID of the user uploading the file

        Returns:
            Dictionary with upload result and file information

        Raises:
            ValueError: If required metadata is missing
        """
        title = metadata.get('title', file.filename)
        content_type = metadata.get('content_type', 'other')
        description = metadata.get('description', '')
        author = metadata.get('author', '')

        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"

        # Determine S3 key based on content type
        if content_type == 'article':
            s3_key = f"articles/{unique_filename}"
        elif content_type == 'web_clip':
            s3_key = f"web-clips/{unique_filename}"
        elif content_type == 'pdf':
            s3_key = f"pdfs/{unique_filename}"
        elif content_type == 'external_video':
            s3_key = f"external-videos/{unique_filename}"
        else:
            s3_key = f"external-content/{unique_filename}"

        # Get file info
        mime_type = mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)

        # Upload to S3
        s3_client = get_s3_client()
        config = get_config()
        bucket = config.s3_bucket

        s3_client.upload_fileobj(
            file,
            bucket,
            s3_key,
            ExtraArgs={
                'ContentType': mime_type,
                'Metadata': {
                    'original_filename': file.filename,
                    'uploaded_by': user_id or 'unknown',
                    'content_type': content_type
                }
            }
        )

        # Create database record
        with DatabaseSession() as db_session:
            item = ExternalContent(
                title=title,
                content_type=content_type,
                description=description,
                author=author,
                original_filename=file.filename,
                s3_key=s3_key,
                s3_bucket=bucket,
                file_size_bytes=file_size,
                file_format=file_extension.lstrip('.').lower(),
                status='uploaded',
                created_by=UUID(user_id) if user_id and user_id != 'demo-user-id' else None
            )
            db_session.add(item)
            db_session.commit()

            # Generate preview URL
            preview_url = s3_client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': s3_key},
                ExpiresIn=86400  # 24 hours for uploads
            )

            return {
                'success': True,
                'id': str(item.id),
                'title': title,
                'content_type': content_type,
                'file_size': file_size,
                'preview_url': preview_url,
                'message': 'File uploaded successfully'
            }