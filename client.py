

import aiohttp
from backend import Status


class DynClient():
    def __init__(self, custom_checker = None):
        self._checker = custom_checker

    async def check_binding(self, libra_address, url):
        if self._checker is None:
            return True
        else:
            return await self._checker(libra_address, url)

    async def check_other_claim(self, claim):
        async with aiohttp.ClientSession() as session:

            if await self.check_binding(claim['vasp_libra_address'], claim['verification_endpoint']):
                async with session.post(claim['verification_endpoint'] + '/check', json=claim) as resp:
                    response = await resp.json()

                return Status[response['status']]
            else:
                return Status.incorrect_address

    async def get_subaddress_from_subaddress(self, url, subaddress):
        request = {
            'subaddress' : subaddress,
        }

        async with aiohttp.ClientSession() as session:

            if await self.check_binding(subaddress, url):
                async with session.post(url + '/generate', json=request) as resp:
                    response = await resp.json()

                return (Status[response['status']], response.get('dynamic_subaddress', None))
            else:
                return Status.incorrect_address

    async def get_attestation(self, originator_record, beneficiary_record, amount):
        request = {
            'beneficiary_travel_rule_record' : beneficiary_record,
            'originator_travel_rule_record'  : originator_record,
            'amount' : amount,
        }

        url = beneficiary_record['verification_endpoint'] + '/attest'

        async with aiohttp.ClientSession() as session:

            if await self.check_binding(beneficiary_record['vasp_libra_address'], beneficiary_record['verification_endpoint']):
                async with session.post(url, json=request) as resp:
                    response = await resp.json()

                if Status[response['status']] != Status.compliance_signature:
                    return Status[response['status']]
                else:
                    return (Status[response['status']], response['reference_id'], response['compliance_signature'])

            else:
                return Status.incorrect_address
