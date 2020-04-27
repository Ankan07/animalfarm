from http_error import invalidUsage
from bson.objectid import ObjectId
from datetime import datetime, timedelta
def reportDeath(input_params, db):

    reqparams = ['type', 'id', 'count']
    for x in reqparams:
        if x not in input_params:
            return invalidUsage('Missing field: ' + x, 400)

    type_box = input_params["type"]
    box_id = input_params["id"]
    no_death = input_params["count"]

    # if the type_box is 'breeder' then there should be a 'death_type'
    # death_type should be neo, dame or sire

    if type_box == "market_selection":

        current = db.market_selection.find_one({"_id": (box_id)})
        
        if current == None:
            return invalidUsage('Invalid box scanned', 400)

        count = current["count"]
        if count - no_death < 0:
            return invalidUsage('No of dead is more than total occupancy', 400)
        else:
            db.market_selection.update({
                "_id": (box_id)
            }, {
                '$set': {
                    "count": count - no_death
                }
            })
            return {'status': 'true'}

    if type_box == "breeder":

        if 'death_type' not in input_params:
            return invalidUsage('Missing field: death_type', 400)
        dtype = input_params['death_type']

        current = db.breeder.find_one({"_id": (box_id)})

        if current == None:
            return invalidUsage('Invalid box scanned', 400)

        if dtype == 'dame':

            count = current["ndames"]
            if count - no_death < 0:
                return invalidUsage('Reported death of dames exceed the total count of dames', 400)
            else:
                db.breeder.update({
                    "_id": (box_id)
                }, {
                    '$set': {
                        "ndames": count - no_death
                    }
                })
                return {'status': 'true'}
    
        if dtype == 'neo':

            # for neo, the batch_id should be sent too
            if 'batch_id' not in input_params:
                return invalidUsage('Missing field: batch_id', 400)

            current = db.batch.find_one({"_id": ObjectId(input_params['batch_id'])})
            if current == None:
                return invalidUsage('Invalid batch selected', 400)

            count = current["count"]
            if count - no_death < 0:
                return invalidUsage('Reported death of neonates is larger than total count', 400)
            else:
                db.batch.update({
                    "_id": ObjectId(input_params['batch_id'])
                }, {
                    '$set': {
                        "count": count - no_death
                    }
                })
                return {'status': 'true'}


def reportBirth(batch_json, db):
    batch_required_variables = ["dob",  "colonyId", "breed", "neocount", "breederId"]
    
    for x in batch_required_variables:
        if x not in batch_json:
            return invalidUsage('Missing field: ' + x, 400).to_dict()
    
    # adding parameters to batch
    
    batch_json["status"] = "neo"
    batch_json["dow"] = datetime.now() + timedelta(days=21)
    batch_json["count"] = batch_json["neocount"]

    
    batch_object = db.batch.insert_one(batch_json)

    task_json = {
        'created_At': datetime.now(),
        'colonyId': batch_json["colonyId"],
        'task': "Required Weaning",
        'status': "incomplete",
        "dueAt":datetime.now() + timedelta(days=21)
    }

    task_object = db.task.insert_one(task_json)

    upres = db.breeder.update({
        "_id": (batch_json["breederId"])
    }, {
        '$push': {
            'batches': str(batch_object.inserted_id),
            'neonates': {
                'batchId': str(batch_object.inserted_id),
                'dob': batch_json['dob']
            }
        }
    })

    return {'status': 'true'} if (upres['updatedExisting'] == True) else {'status': 'false'}