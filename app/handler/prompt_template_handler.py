# app/handlers/prompt_template_handler.py

import json
import os
import uuid
import boto3
from datetime import datetime, timezone
from app.utils.util import logger
from app.models.dynamodb import read_from_dynamodb, add_to_dynamodb, update_item_in_dynamodb, paginate_dynamodb_request

class PromptTemplateHandler:
    """
    Handler for CRUD operations on prompt templates table
    Provides create, read, update, list, and search functionality for prompt templates
    """
   
    def __init__(self):
        """Initialize handler with DynamoDB table names from environment variables"""
        self.dynamodb = boto3.resource('dynamodb')
        self.prompt_templates_table = os.getenv("PROMPT_TEMPLATES_TABLE")
        self.users_table_name = os.getenv("USERS_TABLE")
        self.users_table = self.dynamodb.Table(self.users_table_name)
        self.connect_table = os.getenv("DYNAMO_LAMBDA")
        logger.info(f"Initialized PromptTemplateHandler with tables: {self.prompt_templates_table}, {self.users_table}, {self.connect_table}")
   
    def handle_event(self, event):
        """
        Main entry point for prompt template operations
        Routes incoming requests to appropriate handler methods
        
        Args:
            event: Dictionary containing 'action' and 'payload'
            
        Returns:
            Dictionary with statusCode and body containing response data or error
        """
        action = event.get("action")
        payload = event.get("payload", {})
       
        logger.info(f"Handling action: {action} with payload keys: {list(payload.keys())}")
       
        # Route to appropriate handler method based on action
        if action == "create":
            return self.create_prompt_template(payload)
        elif action == "read":
            return self.get_prompt_template(payload)
        elif action == "update":
            return self.update_prompt_template(payload)
        elif action == "list":
            return self.list_prompt_templates(payload)
        elif action == "list_categories":
            return self.list_all_categories(payload)
        elif action == "search_by_tags":
            return self.search_templates_by_tags(payload)
        elif action == "list_options":
            return self.list_prompt_options(payload)
        else:
            logger.warning(f"Unknown action received: {action}")
            return {
                "statusCode": 400,
                "body": {"error": f"Unknown action: {action}"}
            }
   
    def create_prompt_template(self, payload):
        """
        Create a new prompt template with version tracking
        
        Args:
            payload: Dictionary containing template data including:
                - user_id: Owner of the template
                - role: User role for RBAC
                - category: Template category (Claims, Compliance, etc.)
                - promptTitle: Template title (REQUIRED - as per UI mockup)
                - promptDescription: The actual prompt content/description
                - global: Whether template is global (true/false)
                
        Returns:
            Dictionary with statusCode and created template data
        """
        logger.info("Starting prompt template creation")
        
        # Validate required fields - title is now REQUIRED as per UI mockup
        required_fields = ["user_PK", "role", "category", "promptTitle", "promptDescription"]
        for field in required_fields:
            if field not in payload:
                error_msg = f"Missing required field: {field}"
                logger.error(error_msg)
                return {
                    "statusCode": 400,
                    "body": {"error": error_msg}
                }
        
        # Check if user has permission to create global template
        is_global = payload.get("global", "false").lower() == "true"
        user_role = payload.get("role", "").upper()
        
        # Debug logging to see what's in the payload
        logger.info(f"Payload keys: {list(payload.keys())}")
        logger.info(f"Global value from payload: {payload.get('global')}")
        logger.info(f"Global value type: {type(payload.get('global'))}")
        logger.info(f"is_global calculated: {is_global}")
        logger.info(f"User role: {user_role}")
        
        if is_global and user_role != "ADMIN":
            error_msg = "Only ADMIN users can create global templates"
            logger.error(error_msg)
            return {
                "statusCode": 403,
                "body": {"error": error_msg}
            }
        
        # Generate unique ID and timestamp
        promptTemplate_PK = f"pt{str(uuid.uuid4())}"
        current_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
        
        # Create initial version for version history
        initial_version = {
            "versionNumber": 1,
            "content": payload["promptDescription"],
            "updatedBy": payload["user_PK"],
            "auditLastUpdateDateTime": current_time
        }
        
        # Build template data structure with consistent naming
        template_data = {
            "promptTemplate_PK": promptTemplate_PK,
            "user_PK": payload["user_PK"],
            "role": payload["role"],
            "category": payload["category"],
            "title": payload["promptTitle"],  
            "content": payload["promptDescription"],  
            "versions": [initial_version],
            "auditCreateDateTime": current_time,
            "auditLastUpdateDateTime": current_time,
            "global": "true" if is_global else "false"  # Set based on payload and permissions
        }
        
        # For global templates, add additional metadata
        if is_global:
            template_data["createdByAdmin"] = payload["user_PK"]
            template_data["globalAccess"] = "all"
            logger.info(f"Creating GLOBAL template for category: {payload['category']}")
        else:
            logger.info(f"Creating USER-SPECIFIC template for category: {payload['category']}")
        
        try:
            # Write to DynamoDB using environment variable for table name
            write_result = add_to_dynamodb(self.prompt_templates_table, template_data, self.connect_table)
            logger.info(f"Database write result: {write_result}")
            
            if write_result:
                template_type = "global" if is_global else "user-specific"
                logger.info(f"Successfully created {template_type} prompt template: {promptTemplate_PK}")
                return {
                    "statusCode": 200,
                    "body": {
                        "message": f"Prompt template created successfully ({template_type})",
                        "promptTemplate_PK": promptTemplate_PK,
                        "global": is_global,
                        "template": template_data
                    }
                }
            else:
                error_msg = "Failed to write prompt template to database"
                logger.error(error_msg)
                return {
                    "statusCode": 500,
                    "body": {"error": error_msg}
                }
            
        except Exception as e:
            error_msg = f"Error creating prompt template: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": {"error": error_msg}
            }
   
    def get_prompt_template(self, payload):
        """
        Retrieve a specific prompt template by promptTemplateId and user_id
        
        Args:
            payload: Dictionary containing:
                - promptTemplateId: Unique identifier of the template
                - user_id: Owner of the template for access control
                
        Returns:
            Dictionary with statusCode and template data or error
        """
        promptTemplate_PK = payload.get("promptTemplate_PK")
        user_PK = payload.get("user_PK")
       
        # Validate input parameters
        if not promptTemplate_PK or not user_PK:
            error_msg = "Missing promptTemplateId or user_PK"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": {"error": error_msg}
            }
       
        logger.info(f"Retrieving prompt template with ID: {promptTemplate_PK}")
       
        # Read template from DynamoDB using composite key and environment variable for table name
        template = read_from_dynamodb(self.prompt_templates_table, {
            "promptTemplate_PK": promptTemplate_PK,
            "promptTemplate_PK": user_PK
        })
       
        if template:
            logger.info(f"Successfully retrieved prompt template: {promptTemplate_PK}")
            return {
                "statusCode": 200,
                "body": {
                    "message": "Prompt template retrieved successfully",
                    "template": template
                }
            }
        else:
            error_msg = f"Prompt template not found with ID: {promptTemplate_PK}"
            logger.warning(error_msg)
            return {
                "statusCode": 404,
                "body": {"error": error_msg}
            }
   
    def update_prompt_template(self, payload):
        """
        Update an existing prompt template with version tracking
        
        Args:
            payload: Dictionary containing:
                - promptTemplateId: Template to update
                - user_id: Owner for authorization
                - promptDescription: New content/description 
                - category: New category 
                - promptTitle: New title 
                
        Returns:
            Dictionary with statusCode and update result
        """
        promptTemplate_PK = payload.get("promptTemplate_PK")
        user_PK = payload.get("user_PK")
        new_content = payload.get("promptDescription", '')
       
        # Validate input parameters
        if not promptTemplate_PK or not user_PK:
            error_msg = "Missing promptTemplate_PK or user_PK"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": {"error": error_msg}
            }
       
        logger.info(f"Updating prompt template: {promptTemplate_PK}")
       
        try:
            # Get existing template to verify existence and ownership using environment variable for table name
            existing_template = read_from_dynamodb(
                table_name=self.prompt_templates_table,
                key={
                    "promptTemplate_PK": promptTemplate_PK,
                    "user_PK": user_PK
                }
            )
           
            if not existing_template:
                error_msg = f"Prompt template not found with ID: {promptTemplate_PK}"
                logger.warning(error_msg)
                return {
                    "statusCode": 404,
                    "body": {"error": error_msg}
                }
           
            # Prepare update data with new version
            current_time = datetime.now(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")
            current_versions = existing_template.get("versions", [])
            next_version_number = len(current_versions) + 1
           
            # Create new version entry for audit trail
            new_version = {
                "versionNumber": next_version_number,
                "content": new_content,
                "updatedBy": user_PK,
                "auditLastUpdateDateTime": current_time
            }
           
            # Update versions list (keep last 10 versions for storage efficiency)
            updated_versions = current_versions + [new_version]
            if len(updated_versions) > 10:
                updated_versions = updated_versions[-10:]
           
            # Build fields to update with consistent naming
            update_fields = {
                "content": new_content,
                "versions": updated_versions,
                "auditLastUpdateDateTime": current_time
            }
           
            # Include optional fields if provided with consistent naming
            if "category" in payload:
                update_fields["category"] = payload["category"]
            if "promptTitle" in payload:
                update_fields["title"] = payload["promptTitle"]
           
            # Perform the update in DynamoDB using environment variable for table name
            update_result = self.update_template_fields(
                promptTemplate_PK,
                user_PK,
                update_fields
            )
           
            if update_result:
                logger.info(f"Successfully updated prompt template: {promptTemplate_PK}")
                return {
                    "statusCode": 200,
                    "body": {
                        "message": "Prompt template updated successfully",
                        "promptTemplate_PK": promptTemplate_PK,
                        "versionNumber": next_version_number
                    }
                }
            else:
                error_msg = f"Failed to update prompt template: {promptTemplate_PK}"
                logger.error(error_msg)
                return {
                    "statusCode": 500,
                    "body": {"error": error_msg}
                }
           
        except Exception as e:
            error_msg = f"Error updating prompt template: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": {"error": error_msg}
            }
   
    def list_prompt_templates(self, payload):
        """
        List prompt templates with hierarchical filtering:
        1. Get all templates for user (default)
        2. Filter by categories and/or options
        3. Apply sorting and limiting

        Args:
            payload: Dictionary containing filters:
                - user_id: Required - templates for this user
                - categories: Optional - array of categories to filter by
                - options: Optional - array with ["Global"], ["User"], or ["All"] (default: ["All"])
                - sort_by: Optional - field to sort by (default: updatedAt)
                - sort_order: Optional - asc/desc (default: desc)
                - limit: Optional - max results (default: 100)
                
        Returns:
            Dictionary with statusCode and list of templates
        """
        user_PK = payload.get("user_PK")
        categories = payload.get("categories") or payload.get("category", [])
        options = payload.get("options", ["All"])
        sort_by = payload.get("sortBy", "updatedAt")
        sort_order = payload.get("sortOrder", "desc")
        limit = payload.get("limit", 10)
        page_index = payload.get("pageIndex", 1)
        
        # Handle input formatting
        if isinstance(categories, str):
            categories = [categories]
        categories = [c.strip().title() for c in categories if c]

        if isinstance(options, str):
            options = [options] if options else ["All"]
        options = [opt.strip().lower() for opt in options]    

        logger.info(f"Listing templates for user: {user_PK}, categories: {categories}, options: {options}")
        
        try:            
            # STEP 1: Get user's role
            user_role = None
            user_categories = []
            try:
                user_data = self.users_table.get_item(Key={"user_PK": user_PK})        
                if user_data and "Item" in user_data:
                    item = user_data["Item"]
                    user_role = item.get("role", "").upper()
                    user_categories = [c.strip().title() for c in item.get("category", [])]
                    logger.info(f"User role: {user_role}, categories: {user_categories}")
            except Exception as e:
                logger.warning(f"Could not fetch user data: {str(e)}")

            if categories:
                categories = [c for c in categories if c in user_categories]
            else:
                categories = user_categories
            
            # STEP 2: Determine what to fetch based on options filter
            fetch_global = "global" in options or "all" in options
            fetch_user = "user" in options or "all" in options

            # if len(categories) == 1 and categories[0] == "Personal":
            #     logger.info("Category is ONLY 'personal' - applying special rules")
            #     if "global" in options:
            #         # Global option should return empty
            #         return {
            #             "statusCode": 200,
            #             "body": {
            #                 "templates": [],
            #                 "count": 0,
            #                 "global_count": 0,
            #                 "user_count": 0,
            #                 "filters_applied": {
            #                     "user_PK": user_PK,
            #                     "categories": categories,
            #                     "options": options,
            #                     "sort_by": sort_by,
            #                     "sort_order": sort_order,
            #                     "limit": limit,
            #                     "pageIndex": page_index
            #                 },
            #                 "totalCount": 0,
            #                 "totalPages": 0,
            #                 "message": "No global templates for personal category"
            #             }
            #         }
            #     # For 'user' or 'all', force fetch_user only
            #     fetch_global = False
            #     fetch_user = True
            #     options = ["user"]
            
            logger.info(f"Fetch global: {fetch_global}, Fetch user: {fetch_user}")
            
            # STEP 3: Get user's templates first (this should always work)
            user_templates = []
            if fetch_user:
                user_filters = {}
                if len(categories) == 1:
                    user_filters["category"] = categories[0]

                user_templates = read_from_dynamodb(
                    table_name=self.prompt_templates_table,
                    index_name="PromptTemplatesByUser",
                    partition_key="user_PK",
                    partition_value=user_PK,
                    sort_key="auditLastUpdateDateTime",
                    sort_desc=(sort_order.lower() == "desc"),
                    limit=1000,
                    filters=user_filters
                ) or []

                if len(categories) > 1:
                    user_templates = [
                        t for t in user_templates
                        if t.get("category", "").strip().title() in categories
                    ]                

                if "user" in options and "global" not in options:
                    user_templates = [
                        t for t in user_templates
                        if str(t.get("global", "")).strip().lower() != "true"]           
                logger.info(f"Found {len(user_templates)} user templates")
            
            # STEP 4: Get global templates (if requested and user is ADMIN)
            global_templates = []
            if fetch_global:
                try:
                    if categories:
                        for category in categories:
                            category_templates  = read_from_dynamodb(
                                table_name=self.prompt_templates_table,
                                index_name="PromptTemplatesByCategory",
                                partition_key="category",
                                partition_value=category,
                                sort_key="auditLastUpdateDateTime",
                                sort_desc=(sort_order.lower() == "desc"),
                                limit=limit*2)
                                
                            category_templates = [
                            t for t in category_templates
                            if t.get("global", "").strip().lower() == "true"]
                            global_templates.extend(category_templates)

                    else:
                        # For multiple categories or no category filter, we'll handle post-filtering
                        # First get all templates and then filter
                        global_templates  = read_from_dynamodb(
                            table_name=self.prompt_templates_table,
                            index_name="GlobalTemplatesIndex",
                            partition_key="global",
                            partition_value="true",  # Using same user_id but filtering by global flag
                            sort_key="auditLastUpdateDateTime",
                            sort_desc=(sort_order.lower() == "desc"),
                            limit=limit * 2  # Get more to account for filtering
                        ) or []

                        global_templates = [
                        t for t in global_templates
                        if str(t.get("global", "")).strip().lower() == "true" and
                        (not categories or t.get("category", "").strip().title() in categories)]

                    logger.info(f"Found {len(global_templates)} global templates")
                        
                        # if all_templates_temp:
                        #     global_templates = all_templates_temp
                            
                except Exception as e:
                    logger.warning(f"Could not fetch global templates: {str(e)}")
                    global_templates = []
                
                logger.info(f"Found {len(global_templates)} global templates")
            
            # STEP 5: Combine templates - global first, then user's templates
            seen_ids = set()
            all_templates = []
            
            # # Add global templates first
            # for template in global_templates:
            #     template_id = template.get('promptTemplateId')
            #     if template_id and template_id not in seen_ids:
            #         seen_ids.add(template_id)
            #         # Apply category filter for multiple categories
            #         if not categories or template.get('category') in categories:
            #             all_templates.append(template)
            
            # # Add user templates
            # for template in user_templates:
            #     template_id = template.get('promptTemplateId')
            #     if template_id and template_id not in seen_ids:
            #         seen_ids.add(template_id)
            #         # Apply category filter for multiple categories
            #         if not categories or template.get('category') in categories:
            #             all_templates.append(template)

            for template in global_templates + user_templates:
                template_id = template.get('promptTemplate_PK')
                if template_id and template_id not in seen_ids:
                    seen_ids.add(template_id)
                    all_templates.append(template)
            
            # STEP 6: Sort templates (global first, then by sort field)
            def normalize_sort_value(val):
                # Handle missing or mixed types gracefully
                if val is None:
                    return ""
                return val

            is_desc = (sort_order.lower() == "desc")

            def sort_key_func(t):
                is_global = str(t.get('global', '')).strip().lower() == 'true'
                primary = 0 if is_global else 1
                secondary_raw = normalize_sort_value(t.get(sort_by))

                return (primary, secondary_raw)

            # First, sort by secondary ascending
            all_templates = sorted(all_templates, key=lambda t: normalize_sort_value(t.get(sort_by)) )

            # Then, sort stably by primary so global come first (stable sort preserves previous order)
            all_templates = sorted(all_templates, key=lambda t: 0 if str(t.get('global','')).strip().lower()=='true' else 1)

            # If descending is requested, reverse within each group while keeping global-first
            if is_desc:
                globals_group = [t for t in all_templates if str(t.get('global','')).strip().lower()=='true']
                users_group   = [t for t in all_templates if str(t.get('global','')).strip().lower()!='true']
                globals_group.sort(key=lambda t: normalize_sort_value(t.get(sort_by)), reverse=True)
                users_group.sort(key=lambda t: normalize_sort_value(t.get(sort_by)), reverse=True)
                all_templates = globals_group + users_group


            # STEP 7: Paginate results
            page_items, total_count, total_pages = paginate_dynamodb_request(
                items=all_templates,
                page_size=limit,
                page_index=page_index
            )
            
            # STEP 8: Apply final limit
            # if len(all_templates) > limit:
            #     all_templates = all_templates[:limit]
            
            # STEP 9: Count templates by type for response
            global_count = sum(1 for t in all_templates if t.get('global', '').strip().lower() == 'true')
            user_count = len(all_templates) - global_count
            
            # STEP 9: Build response message based on filters
            message = self.build_response_message(len(all_templates), global_count, user_count, 
                                                 categories, options)
            
            logger.info(f"Successfully listed {len(all_templates)} templates")
            
            return {
                "statusCode": 200,
                "body": {
                "templates": page_items,
                "count": len(page_items),
                "global_count": global_count,
                "user_count": user_count,
                "filters_applied": {
                    "user_PK": user_PK,
                    "categories": categories,
                    "options": options,
                    "sort_by": sort_by,
                    "sort_order": sort_order,
                    "limit": limit,
                    "pageIndex": page_index
                },
                "totalCount": total_count,
                "totalPages": total_pages,
                "message": message
                }
            }
            
        except Exception as e:
            error_msg = f"Error listing prompt templates: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": {"error": error_msg}
            }


    def build_response_message(self, total_count, global_count, user_count, categories, options):
        """
        Build descriptive message based on applied filters
        """

        options = [opt.strip().lower() for opt in options]
        if not categories and "all" in options:
            return f"Found {total_count} templates ({global_count} global, {user_count} user) - all categories"
        
        elif categories and "all" in options:
            return f"Found {total_count} templates ({global_count} global, {user_count} user) for categories {categories}"
        
        elif "global" in options and "user" not in options:
            if categories:
                return f"Found {total_count} global templates for categories {categories}"
            else:
                return f"Found {total_count} global templates - all categories"
        
        elif "user" in options and "global" not in options:
            if categories:
                return f"Found {total_count} user templates for categories {categories}"
            else:
                return f"Found {total_count} user templates - all categories"
        
        else:
            return f"Found {total_count} templates with custom filters"
     
    def list_all_categories(self, payload):
        """
        List all unique categories available for a user's templates
        
        Args:
            payload: Dictionary containing:
                - user_id: User to get categories for
                
        Returns:
            Dictionary with statusCode and list of unique categories
        """
        user_PK = payload.get("user_PK")
       
        logger.info("Listing all categories for user: {user_PK}")
       
        try:
            # Get user's templates to extract categories using environment variable for table name
            response = self.users_table.get_item(Key={"user_PK": user_PK})
            user_data = response.get("Item")
           
            if not user_data:
                logger.warning(f"No user found with ID: {user_PK}")
                return {
                    "statusCode": 404,
                    "body": {"error": f"User not found with ID: {user_PK}"}
                }
           
            # Extract unique categories and sort alphabetically
            categories = user_data.get("category", [])
            if isinstance(categories, str):
                categories = [categories]
            categories = [c.strip() for c in categories if c]

            categories = sorted(set(categories))
            logger.info(f"Found {len(categories)} categories for user {user_PK}")

            return {
                "statusCode": 200,
                "body": {
                    "categories": categories,
                    "count": len(categories)
                }
            }
           
        except Exception as e:
            error_msg = f"Error listing categories: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": {"error": error_msg}
            }
   
    def search_templates_by_tags(self, payload):
        """
        Search prompt templates by tags with optional category filtering
        
        Args:
            payload: Dictionary containing:
                - tags: List of tags to search for
                - user_id: User whose templates to search
                - category: Optional category filter
                
        Returns:
            Dictionary with statusCode and matching templates
        """
        tags = payload.get("tags", [])
        user_PK = payload.get("user_PK")

        #Normalize options
        option = payload.get("options", "All")
        if not isinstance(option, str):
            option = "All"
        option = option.strip().title()
           
        # Validate search tags are provided
        if not tags:
            error_msg = "Missing tags for search"
            logger.error(error_msg)
            return {
                "statusCode": 400,
                "body": {"error": error_msg}
            }
       
        logger.info(f"Searching templates by tags: {tags}")
       
        try:
            user_categories = []
            try:
                user_data = self.users_table.get_item(Key={"user_PK": user_PK})
                if user_data and "Item" in user_data:
                    item = user_data["Item"]
                    user_categories = [c.strip().title() for c in item.get("category", [])]
                    logger.info(f"User {user_PK} categories: {user_categories}")
            except Exception as e:
                logger.warning(f"Could not fetch user data: {str(e)}")

            # Normalize categories
            categories = payload.get("category", [])
            if isinstance(categories, str):
                categories = [categories]
            categories = [c.strip().title() for c in categories if c]

            if not categories:  # default to all categories user has access to
                categories = user_categories

            logger.info(f"Effective categories for search: {categories}")

            templates = []
            
            if option in ["All", "User"]:
                user_templates = read_from_dynamodb(
                table_name=self.prompt_templates_table,
                index_name="PromptTemplatesByUser",
                partition_key="user_PK",
                partition_value=user_PK,
                sort_key="auditLastUpdateDateTime",
                sort_desc=True,
                limit=1000) or []

                templates.extend(user_templates)
            
            if option in ["All", "Global"]:
                global_templates = read_from_dynamodb(
                table_name=self.prompt_templates_table,
                index_name="GlobalTemplatesIndex",
                partition_key="global",
                partition_value="true",
                sort_key="auditLastUpdateDateTime",
                sort_desc=True,
                limit=1000) or []

                templates.extend(global_templates)
            
            logger.info(f"Found {templates} from the table")

            # Filter templates that contain any of the search tags
            matching_templates = []
            search_tags_lower = [t.lower().strip() for t in tags]

            for template in templates:
                raw_tags = template.get("tags")
                matched = False

                if raw_tags:
                    # Normalize tags from record
                    if isinstance(raw_tags, str):
                        template_tags = [t.lower().strip() for t in raw_tags.split(",") if t.strip()]
                    elif isinstance(raw_tags, list):
                        template_tags = [t.lower().strip() for t in raw_tags]
                    else:
                        template_tags = []

                    # Match against record tags
                    if any(tag in template_tags for tag in search_tags_lower):
                        matched = True
                else:
                    # No tags in record → search payload tags in title/content
                    title = template.get("title", "").lower()
                    content = template.get("content", "").lower()
                    if any(tag in title or tag in content for tag in search_tags_lower):
                        matched = True

                # Apply category filter if matched
                template_category = template.get("category", "").strip().title()
                if matched and (not template_category or template_category in categories):
                    matching_templates.append(template)
           
            # Sort results by most recently updated
            matching_templates.sort(
                key=lambda x: (
                    0 if x.get("global") == "true" else 1,   # global first
                    x.get("auditLastUpdateDateTime","")  # then by time
                ),
                reverse=True
            )
           
            logger.info(f"Found {len(matching_templates)} templates matching tags: {tags}")

           
            return {
                "statusCode": 200,
                "body": {
                    "templates": matching_templates,
                    "search_tags": tags,
                    "count": len(matching_templates)
                }
            }
           
        except Exception as e:
            error_msg = f"Error searching templates by tags: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": {"error": error_msg}
            }
   
    def sort_templates(self, templates, sort_by="auditLastUpdateDateTime", sort_order="desc"):
        """
        Sort templates by specified field and order
        
        Args:
            templates: List of template dictionaries to sort
            sort_by: Field to sort by (updatedAt, createdAt, category, title)
            sort_order: Sort direction (asc, desc)
            
        Returns:
            Sorted list of templates
        """
        try:
            reverse = sort_order.lower() == "desc"
           
            # Select appropriate key function based on sort field
            if sort_by == "auditCreateDateTime":
                key_func = lambda x: x.get('auditCreateDateTime', '')
            elif sort_by == "category":
                key_func = lambda x: x.get('category', '')
            elif sort_by == "title":
                key_func = lambda x: x.get('title', '')
            else:  # Default to updatedAt
                key_func = lambda x: x.get('auditLastUpdateDateTime', '')
           
            return sorted(templates, key=key_func, reverse=reverse)
           
        except Exception as e:
            logger.warning(f"Error sorting templates, returning unsorted: {str(e)}")
            return templates
   
    def update_template_fields(self, promptTemplate_PK, user_PK, fields_dict):
        """
        Helper method to update multiple fields in template record
        
        Args:
            prompt_template_id: ID of template to update
            user_id: Owner of template
            fields_dict: Dictionary of field names and values to update
            
        Returns:
            Boolean indicating success of update operation
        """
        try:
            # Build DynamoDB update expression
            update_expression = "SET " + ", ".join([
                f"#{field} = :{field}" for field in fields_dict.keys()
            ])
            expression_names = {f"#{field}": field for field in fields_dict.keys()}
            expression_values = {f":{k}": v for k, v in fields_dict.items()}
           
            # Execute update operation using environment variable for table name
            update_result = update_item_in_dynamodb(
                table_name=self.prompt_templates_table,
                key={
                    "promptTemplate_PK": promptTemplate_PK,
                    "user_PK": user_PK
                },
                update_expression=update_expression,
                expression_attribute_values=expression_values,
                expression_attribute_names=expression_names
            )
           
            return update_result is not None
           
        except Exception as e:
            logger.error(f"Error updating template fields: {str(e)}")
            return False
        
    def list_prompt_options(self, payload):
        """
        List available prompt options for dropdowns.
        Logic:
        - If category list is exactly ['Personal'] -> options = ['User']
        - If category list includes 'Personal' + others -> options = ['All', 'User', 'Global']
        - If category list excludes 'Personal' -> options = ['All', 'User', 'Global']

        Args:
            payload: Dictionary containing filters (expects 'categories' or 'category' as a list)

        Returns:
            Dictionary with statusCode and list of options
        """
        try:
            # Extract categories from payload (always a list by contract)
            categories = payload.get("categories") or payload.get("category", [])
            categories = [c.strip().title() for c in categories if c]  # normalize casing

            # Decision logic
            if len(categories) == 1 and categories[0] == "Personal":
                options = ["User"]
            else:
                options = ["All", "Global", "User"]

            logger.info(f"Categories: {categories}, Options returned: {options}")

            return {
                "statusCode": 200,
                "body": {
                    "options": options,
                    "count": len(options),
                    "message": f"Found {len(options)} available options for categories {categories}"
                }
            }

        except Exception as e:
            error_msg = f"Error listing prompt options: {str(e)}"
            logger.error(error_msg)
            return {
                "statusCode": 500,
                "body": {"error": error_msg}
            }


# Lambda handler function
def handler(event, context):
    """
    AWS Lambda handler for prompt template operations
    Main entry point for AWS Lambda invocations
    
    Args:
        event: Lambda event data
        context: Lambda context object
        
    Returns:
        Response from PromptTemplateHandler
    """
    logger.info("Prompt template handler invoked")
    prompt_template_handler = PromptTemplateHandler()
    return prompt_template_handler.handle_event(event)
