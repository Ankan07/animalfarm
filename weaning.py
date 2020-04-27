from http_error import invalidUsage
from bson.objectid import ObjectId
from datetime import datetime

def completeWeaning(input_params, db):
    reqparams = ['breederId', 'batchId']
    print('im here on complete weaning')
    for x in reqparams:
        if x not in input_params:
            print('invalid usage ' + x)
            return invalidUsage('Missing field: ' + x, 400)
    res = db.breeder.update_one({'_id': input_params['breederId']}, {
        '$pull': {
            'neonates': {'batchId':input_params['batchId']}
        }
    })
    print(res.raw_result)
    if res is None:
        return invalidUsage('writing to database failed', 400)
    #print(res.raw_result)
    return {'status': True}


# Send something like this
# {
#     'mmd': {
#         'mmqr': {
#             "data": {
#                 "id":"",
#                 'type':""
#                 },
#             'type': '',
#             'batchId':""
#         },
#     'mma':[{
#         'value':'21',
#         'box':'market',
#         'gender': 'male'
#     }]
#     }
# }
def getWeaningData(input, db):
    if 'id' not in input:
        return invalidUsage('id not found!', 400)
    batchId = input['id']

    data = {}
    res = db.batch.find_one({'_id': ObjectId(batchId)})
    if res is None:
        return invalidUsage('invalid batch', 403)
    keys = ['mm', 'mf', 'sm', 'sf']
    #print(res)
    for k in keys:
        key = k + 'boxId'
        if key in res:
        #     data[k] = 0
        # else:
            #print('trying to get ' + k)
            # TODO, get this shit right
            smbox = db.market_selection.find_one({'_id': (res[key])})
            if smbox is None:
                return invalidUsage('selection/male box is none for: ' + res[key], 500)
            data[k] = smbox['count']
    
    return data

def addWeaningData(input_params, db):
    reqParams = ['weight', 'type', 'containerId', 'batchId']
    for x in reqParams:
        if x not in input_params:
            return invalidUsage('Missing field: ' + x, 400)
    
    # add data to batch
    # create a market_selection document with containerId
    res = db.batch.update_one({'_id': ObjectId(input_params['batchId'])}, {'$set': {
        input_params['type']: input_params['containerId']
    }})

    if res is None:
        return invalidUsage('something seriously went wrong', 500)
    # #print(res['raw_result'])
    res = db.batch.find_one({'_id': ObjectId(input_params['batchId'])})
    if res is None:
        return invalidUsage('batch not found, what on earth is happening?', 500)
    res = db.market_selection.update_one({'_id': input_params['containerId']},
    {
        '$set': {
        'batchId': input_params['batchId'],
        'colonyId': res['colonyId'],
        'gender': input_params['type'][1],
        'count': len(input_params['weight']),
        'dob': res['dob'],
        'dow': str(datetime.now()),
        'weight': [x['value'] for x in input_params['weight']],
        'weight_taken_at': str(datetime.now())
    }}, upsert=True)

    if res is None:
        return invalidUsage('failed to write to database', 500)
    
    return {'status': True}

def verifyContainer(input_params, db):
    reqParams = ['batchId', 'colonyId', 'boxType', 'qr']
    for x in reqParams:
        if x not in input_params:
            return invalidUsage('Missing field: ' + x, 400)
    
    for x in ['id', 'type']:
        if x not in input_params['qr']:
            return invalidUsage('Missing field: ' + x, 400)
    qr = input_params['qr']
    # if this box was previously partial weaned, then match previous id with current id
    # if not previously weaned, then check if this box is used somewhere else

    # check box types
    type_map = {
        'mmboxId': 'M',
        'mfboxId': 'M',
        'smboxId': 'S',
        'sfboxId': 'S'
    }
    if input_params['boxType'] not in type_map:
        return {'isValid': False, 'message': input_params['boxType'] + ' not found in ' + str(type_map.keys())}
    if (type_map[input_params['boxType']] != qr['type']):
        return {'isValid': False}
    
    res = db.batch.find_one({'_id': ObjectId(input_params['batchId'])})
    if res != None:
        # previously weaned
        if input_params['boxType'] in res:
            # Some entry on this particular box type found, match with provided scanned box id
            existing_id = res[input_params['boxType']]
            if existing_id == qr['id']:
                # same box, return existing list
                msbox = db.market_selection.find_one({'_id': res[input_params['boxType']]})
                if msbox == None:
                    return invalidUsage('The programmer messed it up, God bless him', 500)
                return {'isValid':True, 'weight': msbox['weight']}
            else:
                return {'isValid': False}
    # find if this box is used anywhere else
    res = db.market_selection.find_one({'_id': qr['id']})
    if res == None:
        # not used anywhere else, good to go
        return {'isValid': True, 'weight': []}
    
    # For every other condition, these boxes ain't loyal
    return {'isValid': False}