import pandas as pd
import json
from sentence_transformers import SentenceTransformer

# Initialize Sentence-BERT model
model = SentenceTransformer('all-MiniLM-L6-v2')

# Function to process and vectorize reviews for a product
def process_reviews(reviews):
    """Vectorize each review and return the average vector."""
    if reviews and reviews.strip():  # Check if reviews exist and are not just whitespace
        review_list = reviews.split(',')  # Split reviews into individual comments
        review_vectors = model.encode(review_list)  # Vectorize each review separately
        review_vector = review_vectors.mean(axis=0)  # Calculate average of review vectors
        return review_vector
    else:
        return None  # No reviews available

def process_search(search):
    if search and search.strip():  # Added check for empty string
        search_list = search.split(',')
        search_vectors = model.encode(search_list)
        search_vector = search_vectors.mean(axis=0)
        return search_vector
    return None

# Function to combine product data and reviews to create a vector
def combine_product_with_reviews(product_data):
    """Combine product metadata and the review essence to generate a combined vector."""
    # Handle potential None values or convert numeric types to strings
    name = str(product_data.get('name', '')) if product_data.get('name') is not None else ''
    rating = str(product_data.get('rating', 0)) if product_data.get('rating') is not None else '0'
    category = str(product_data.get('category', '')) if product_data.get('category') is not None else ''
    description = str(product_data.get('description', '')) if product_data.get('description') is not None else ''
    
    combined_text = f"Product Name: {name}, Rating: {rating}, " \
                    f"Category: {category}, " \
                    f"Description: {description}"
    
    product_vector = model.encode(combined_text)  # Vectorize the product metadata
    
    # Only process reviews if they exist
    reviews = product_data.get('reviews', '')
    review_vector = process_reviews(reviews)  # Vectorize the reviews
    
    if review_vector is not None:
        combined_vector = product_vector + review_vector  # Combine the product vector and review vector
    else:
        combined_vector = product_vector  # If no reviews, just use the product data
    
    return combined_vector

# Vectorize all products with reviews
def vectorize_product_with_reviews(df):
    """Vectorize all products in the dataframe."""
    product_vectors = []
    try:
        for _, product in df.iterrows():
            product_vector = combine_product_with_reviews(product)
            product_vectors.append(product_vector)
    except Exception as e:
        # Print any errors for debugging
        print(f"Error in vectorize_product_with_reviews: {str(e)}")
        # Return a default vector if processing fails
        default_vector = model.encode("default product")
        product_vectors.append(default_vector)
    
    return product_vectors

def combine_user_with_search(user_data):
    """
    Combine user data with their search history to create a vector representation.
    Handles empty product and search fields for new users.
    """
    # Handle empty product and search fields gracefully
    product = user_data.get('product', '') if user_data.get('product') else "new_user"
    search = user_data.get('search', '') if user_data.get('search') else "no_search_history"
    user_id = str(user_data.get('user_id', '')) if user_data.get('user_id') is not None else ''
    
    combined_text = f"user_id: {user_id}, product: {product}"
    user_vector = model.encode(combined_text)
    
    # Only process search if it's not empty
    if search != "no_search_history":
        search_vector = process_search(search)
        if search_vector is not None:
            combined_vector = user_vector + search_vector
        else:
            combined_vector = user_vector
    else:
        # For new users without search history, just use the base user vector
        combined_vector = user_vector
        
    return combined_vector

def vectorize_user_with_search(df):
    """Vectorize all users in the dataframe, handling new users properly."""
    user_vectors = []    
    for _, user in df.iterrows():
        try:
            user_vector = combine_user_with_search(user)
            user_vectors.append(user_vector)
        except Exception as e:
            # Fallback for any errors - create a default vector
            print(f"Error creating vector for user {user.get('user_id', 'unknown')}: {str(e)}")
            # Create a default vector with the same dimensions as your model outputs
            default_vector = model.encode("new user default")
            user_vectors.append(default_vector)
    
    return user_vectors