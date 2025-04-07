from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

def calculate_food_total(food_items):
    """Calculate the food total from a list of items."""
    total = Decimal('0.00')
    if not isinstance(food_items, list):
        logger.warning("foodItems is not a list, returning 0.00 for food total.")
        return total
        
    for item in food_items:
        try:
            price = Decimal(str(item.get('price', 0)))
            quantity = Decimal(str(item.get('quantity', 0)))
            total += price * quantity
        except Exception as e:
            logger.error(f"Error processing food item {item}: {e}", exc_info=True)
            # Decide if you want to skip the item or raise an error
            # Skipping for now
            continue
    return total

def calculate_delivery_fee(location):
    """Calculate delivery fee based on location."""
    # In a real implementation, this would use distance or zones
    # For now, return a fixed fee.
    # Add basic validation if needed
    if not isinstance(location, str):
         logger.warning("deliveryLocation is not a string, using default fee.")
         
    # Example: Could add logic based on location string later
    # if "far away" in location.lower():
    #     return Decimal('5.99')
        
    return Decimal('3.99')
