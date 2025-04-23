def safe_call(func, *args, **kwargs):
    """
    Safely call a function and handle any exceptions.
    
    Args:
        func: The function to call
        *args: Positional arguments to pass to the function
        **kwargs: Keyword arguments to pass to the function
        
    Returns:
        The result of the function call, or None if an exception occurred
    """
    try:
        return func(*args, **kwargs)
    except Exception as e:
        print(f"Error calling {func.__name__}: {e}")
        return None