from bson.json_util import dumps

def getColony(db):
    res = db.colony.find({})
    cols = []
    if res is None:
        return {'message': 'nothing found!'}
    for d in res:
        cols.append(d)
    return dumps(cols)

def getBreeders(db):
    res = db.breeder.find({})
    cols = []
    if res is None:
        return {'message': 'nothing found!'}
    for d in res:
        cols.append(d)
    return dumps(cols)

def getBatch(db):
    res = db.batch.find({})
    cols = []
    if res is None:
        return {'message': 'nothing found!'}
    for d in res:
        cols.append(d)
    return dumps(cols)

def getMS(db):
    res = db.market_selection.find({})
    cols = []
    if res is None:
        return {'message': 'nothing found!'}
    for d in res:
        cols.append(d)
    return dumps(cols)