def find_max(collection, col):
    return collection.find_one(sort=[(col, -1)])


def find_min(collection, col):
    return collection.find_one(sort=[(col, 1)])


def find_id_match(collection, id):
    return collection.find_one({"_id": id})
