def ok(data=None):
    return {"code": 0, "data": data}

def err(code=1, message="error"):
    return {"code": code, "message": message}
