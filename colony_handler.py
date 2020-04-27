from http_error import invalidUsage
def create_colony(input_params, db):
    reqparams = ['breed', 'breeder_ids','sire_batchId','sire_colonyId','colonyname']
    for x in reqparams:
        if x not in input_params:
            return invalidUsage('Missing field: ' + x, 400)


    #define the colony_object
    colony={}
    #get the current colony number.
    colony_number=db.meta.find_one({"type":"colonycount"})
    count=colony_number["count"]
    #increase colony count
    db.meta.update_one({"type":"colonycount"},{'$set':{'count':count+1}})
    #generate colony name
    colonyId='C'+str(count)
    colonyname=input_params['colonyname']
    #fetch selection_box_sire_details step 1
    # sire_details=db.market_selection.find_one({"_id": input_params['sireId']})

    sire_batchId=input_params['sire_batchId']
    sire_colonyId=input_params['sire_colonyId']

    #creating the breeder object step 2
    breeder_ids=input_params['breeder_ids']
    for i in range(len(breeder_ids)):
        breeder_object={}
        temp=breeder_ids[i]
        breederId=temp["breederId"]
        breeder_object["dames"]=temp["dames"]
        breeder_object["ndames"]=len(breeder_object["dames"])
        breeder_object["neonates"]=[]
        breeder_object["_id"]=breederId
        breeder_object["ms"]=[]
        breeder_object["colonyId"]=colonyId
        breeder_object["cName"]=colonyname
   
        breeder_object["breed"]=input_params["breed"]
        db.breeder.insert_one(breeder_object)
    
    #insering colony object
    sire={}
    sire["colonyId"]= sire_colonyId
    sire["batchId"]=sire_batchId
    colony["name"]=colonyname
    colony["sire"]=sire
    colony["generation"]=0
    colony["breeders"]=[x['breederId'] for x in breeder_ids]
    colony["ms"] = []
    colony["rest"] = False
    colony["breed"] = input_params["breed"]
    colony["_id"] = colonyId
    colony['restboxId'] = input_params['restboxId']
 
    db.rest.insert_one({'_id': input_params['restboxId'], 'colonyId': colonyId})
    count = 0
    for x in breeder_ids:
        count += len(breeder_ids['dames'])
    colony['type'] = 'HAREM' if count > 1 else 'INDIVIDUAL'
    
    db.colony.insert_one(colony)

    return {'status':"success"}

def verifyIdentity(body, db):
    reqParams = ['verifyType', 'id', 'type']
    for x in reqParams:
        if x not in body:
            return invalidUsage('missing field ' + x, 400)
    
    qr = {
        'id': body['id'],
        'type': body['type']
    }

    if body['verifyType'] == 'breeder':
        if qr['type'] == 'B':
            res = db.breeder.find_one({'_id': body['id']})
            if res is None:
                return {'isValid': True}
            else:
                return {'isValid': False, 'message': 'breeder already attached to colony'}
        
    elif body['verifyType'] == 'dame' or body['verifyType'] == 'sire':
        
        if qr['type'] == 'Q' or qr['type'] == 'S':
            
            if qr['id'] == 'Q0000':
                # this is universal sink quarantine for preexisting animals
                return {'isValid': True, 'data': {
                    'colonyId': 'C0000',
                    'batchId': 'bt0000'
                }}
            
            # check for quarantine/selection box from market_selection
            res = db.market_selection.find_one({'_id': qr['id']})
            if res is None:
                return {'isValid': False, 'message': 'selection doc not found'}
            else:
                gender = 'm' if body['verifyType'] == 'sire' else 'f'
                if res['gender'] != gender:
                    return {'isValid': False, 'message': 'gender mismatch'}
                return {'isValid': True, 'data': {
                    'colonyId': res['colonyId'],
                    'batchId': res['batchId']
                }}
    elif body['verifyType'] == 'rest':
        if qr['type'] == 'R':
            res = db.rest.find_one({'_id': qr['id']})
            if res is None:
                return {'isValid': True}
    return {'isValid': False, 'message': 'base case'}