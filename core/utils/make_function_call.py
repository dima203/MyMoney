def make_function_call(func: callable, *args):
    return lambda _: func(*args)
