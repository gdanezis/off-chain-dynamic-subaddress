from aiohttp import web
from os import urandom

from backend import ClaimsDB, Status
from client import DynClient

import json

routes = web.RouteTableDef()

class ResponseError(Exception):
    def __init__(self, status):
        self.status = status

@routes.post('/check')
async def check_own_claim(request):
    try:
        claim_db = request.app['db']
        claim = await request.json()

        # Simply check the chaim in the DB and return the status.
        status = await claim_db.check_own_claim(claim)

        response = {
            'status' : status.value
        }
    except Exception as e:
        print(e)
        response = {
            'status' : Status.unexpected_error.value
        }

    print('\n\nRequest (/check):\n')
    print(json.dumps(claim, indent=4))
    print('\nResponse:\n')
    print(json.dumps(response, indent=4))

    return web.json_response(data=response)

@routes.post('/generate')
async def generate_dynamic_subaddress(request):

    try:
        claim_db = request.app['db']
        generation_request = await request.json()

        # Check that the subaddress exists
        subaddress = generation_request['subaddress']
        claim = await claim_db.check_own_dynamic_subaddress(subaddress)
        if claim is None:
            raise ResponseError(Status.invalid_subaddress)

        # Issue and return a fresh subaddress
        status, dyn_subaddr = await claim_db.generate_dynamic_subaddress(claim)
        response = {
            'status' : status.value,
            'dynamic_subaddress': dyn_subaddr,
        }

    except ResponseError as e:
            response = {
                'status' : e.status.value
            }
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(e)
        response = {
            'status' : Status.unexpected_error.value
        }

    print('\n\nRequest (/generate):\n')
    print(json.dumps(generation_request, indent=4))
    print('\nResponse:\n')
    print(json.dumps(response, indent=4))

    return web.json_response(data=response)


@routes.post('/attest')
async def attest(request):

    try:
        claim_db = request.app['db']
        attest_request = await request.json()

        beneficiary_claim = attest_request['beneficiary_travel_rule_record']
        originator_claim = attest_request['originator_travel_rule_record']
        amount = attest_request['amount']

        # Step 1. Check our own claim
        status = await claim_db.check_own_claim(beneficiary_claim)
        if status != Status.correct_record:
            raise ResponseError(status)

        # Step 2. Check the originator claim
        status = await claim_db.client.check_other_claim(originator_claim)
        if status != Status.correct_record:
            raise ResponseError(Status.incorrect_originator_record)

        # Step 3. Check with the risk function whether we want to attest for payment
        risk_ok = await claim_db.call_risk_function(originator_claim, beneficiary_claim, amount)
        if risk_ok is False:
            raise ResponseError(Status.rejected)

        # Step 4. If all good sign a fresh reference_id and return the result
        ref_id, signature = await claim_db.generate_compliance_key_signature(originator_claim, beneficiary_claim, amount)

        response = {
            'status' : Status.compliance_signature.value,
            'reference_id': ref_id,
            'compliance_signature': signature,
        }

    except ResponseError as e:
            response = {
                'status' : e.status.value
            }
    except Exception as e:
        print(e)
        response = {
            'status' : Status.unexpected_error.value
        }

    print('\n\nRequest (/attest):\n')
    print(json.dumps(attest_request, indent=4))
    print('\nResponse:\n')
    print(json.dumps(response, indent=4))

    return web.json_response(data=response)


async def run_service(claims_db, address='0.0.0.0', port=8080):
    app = web.Application()
    app.add_routes(routes)
    app['db'] = claims_db
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, address, port)
    await site.start()
    return runner
