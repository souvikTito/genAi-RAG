# Create simple read dynamo client
import boto3
from app.utils.util import logger
import json
import math
from boto3.dynamodb.conditions import Key, Attr
from datetime import datetime, timedelta

# Initialise lambda client
dynamoDb = boto3.resource('dynamodb', region_name="us-east-2")
lambda_client = boto3.client('lambda', region_name="us-east-2")

# Global function to read data from DynamoDB tables
def read_from_dynamodb(
    table_name: str,
    key: dict = None,
    index_name: str = None,
    partition_key: str = None,
    partition_value: str = None,
    sort_key: str = None,
    days: int = None,
    sort_desc: bool = False,
    limit: int = 50,
    filters: dict = None
):
    print('Starting DynamoDB read operation')

    try:
        table = dynamoDb.Table(table_name)
        logger.info(f"Accessing table: {table_name}")

        # Case 1: Direct get_item — only if both PK and SK are present
        if key:
            if len(key) == 2:
                logger.info(f"Fetching item with key: {key}")
                response = table.get_item(Key=key)
                return response.get("Item")
            else:
                logger.warning(f"Incomplete key provided for get_item: {key}")
                return None

        # Case 2: Query with PK and optional SK range
        if partition_key and partition_value:
            key_expr = Key(partition_key).eq(partition_value)

            # Apply time filter if days and sort_key are provided
            if sort_key and days:
                cutoff = (datetime.utcnow() - timedelta(days=days)).isoformat()
                key_expr &= Key(sort_key).gte(cutoff)

            query_params = {
                "KeyConditionExpression": key_expr,
                "ScanIndexForward": not sort_desc,
                "Limit": limit
            }

            if index_name:
                query_params["IndexName"] = index_name

            if filters:
                filter_expr = None
                for attr_key, attr_val in filters.items():
                    cond = Attr(attr_key).eq(attr_val)
                    filter_expr = cond if not filter_expr else filter_expr & cond
                query_params["FilterExpression"] = filter_expr

            logger.info(f"Querying with params: {query_params}")
            response = table.query(**query_params)
            return response.get("Items", [])

        logger.warning("No valid key or query parameters provided")
        return None

    except Exception as e:
        logger.error(f"Error reading from {table_name}: {str(e)}")
        return None
    
def add_to_dynamodb(table_name:str, item:dict, lambda_name:str):
    try:
        payload = {
            "tableName":table_name,
            "payload":item
        }
        logger.info(f"Payload to write lambda for table {table_name}: {payload}")

        response = lambda_client.invoke(
            FunctionName=lambda_name,
            InvocationType="RequestResponse", 
            Payload=json.dumps(payload)
        )

        db_result = json.load(response['Payload'])
        #logger.info('what returned from write',db_result)

        status_code = response.get("StatusCode")
        if status_code == 200:
            logger.info(f"Successfully invoked Lambda '{lambda_name}' for table '{table_name}'")
            return True
        else:
            logger.warning(f"Lambda '{lambda_name}' returned status {status_code}")
            return False

    except Exception as e:
        logger.error(f"Error invoking Lambda '{lambda_name}': {str(e)}")
        return False


def update_item_in_dynamodb(table_name: str, key: dict, update_expression: str, 
                          expression_attribute_values: dict, expression_attribute_names: dict = None):
    """
    Update an item in DynamoDB table
    
    Args:
        table_name (str): Name of the DynamoDB table
        key (dict): Primary key of the item to update
        update_expression (str): DynamoDB update expression (e.g., "SET #field = :value")
        expression_attribute_values (dict): Values for the update expression
        expression_attribute_names (dict): Attribute names for reserved words
    
    Returns:
        dict: Updated item attributes or None if error
    """
    
    try:
        table = dynamoDb.Table(table_name)
        
        # Prepare update parameters
        update_kwargs = {
            'Key': key,
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_attribute_values,
            'ReturnValues': 'ALL_NEW'  # Return the updated item
        }
        
        # Add expression attribute names if provided (for reserved words)
        if expression_attribute_names:
            update_kwargs['ExpressionAttributeNames'] = expression_attribute_names
        
        # Perform the update
        response = table.update_item(**update_kwargs)
        updated_item = response.get('Attributes', {})
        
        logger.info(f"Successfully updated item in {table_name} with key: {key}")
        logger.debug(f"Updated item: {updated_item}")
        
        return updated_item

    except Exception as e:
        logger.error(f"Error updating item in {table_name}: {str(e)}")
        logger.error(f"Error updating item in {table_name}: {str(e)}")
        return None
    
def paginate_dynamodb_request(
    table_name: str = None,
    gsi_name: str = None,
    partition_key: str = None,
    partition_value: str = None,
    sort_key: str = None,
    items: list = None,
    page_size: int = 10,
    page_index: int = 1
):
    """
    Unified pagination utility.
    - If `items` is provided, paginates the list directly.
    - Otherwise, queries DynamoDB using provided table/index info and paginates results.
    
    Args:
        table_name: DynamoDB table name (required if items not provided)
        gsi_name: DynamoDB index name
        partition_key: Partition key name
        partition_value: Partition key value
        sort_key: Sort key name (optional)
        items: Optional list of items to paginate directly
        page_size: Number of items per page
        page_index: Page number (1-based)
    
    Returns:
        (page_items, total_count, total_pages)
    """
    # Case 1: Use provided list
    if items is not None:
        total_count = len(items)
        total_pages = math.ceil(total_count / page_size)
        start = (page_index - 1) * page_size
        end = start + page_size
        page_items = items[start:end]
        return page_items, total_count, total_pages

    # Case 2: Query DynamoDB
    if not table_name or not gsi_name or not partition_key or not partition_value:
        raise ValueError("Missing required DynamoDB parameters")

    table = dynamoDb.Table(table_name)
    response = table.query(
        IndexName=gsi_name,
        KeyConditionExpression=Key(partition_key).eq(partition_value),
        ScanIndexForward=False
    )

    all_items = response.get("Items", [])
    total_count = len(all_items)
    total_pages = math.ceil(total_count / page_size)
    start = (page_index - 1) * page_size
    end = start + page_size
    page_items = all_items[start:end]

    return page_items, total_count, total_pages
