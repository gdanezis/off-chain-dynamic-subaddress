from enum import Enum
from os import urandom
from copy import deepcopy
from libra_address import LibraAddress

class Status(Enum):
    correct_record = 'correct_record'
    incorrect_record = 'incorrect_record'
    incorrect_originator_record = 'incorrect_originator_record'
    unexpected_data = 'unexpected_data'
    incorrect_address = 'incorrect_address'
    fresh_dynamic_subaddress = 'fresh_dynamic_subaddress'
    invalid_subaddress = 'invalid_subaddress'
    unknown_command = 'unknown_command'
    rejected = 'rejected'
    unexpected_error = 'unexpected_error'
    compliance_signature = 'compliance_signature'
    missing_identifier = 'missing_identifier'
    missing_endpoint = 'missing_endpoint'


class DynServiceError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message

class ClaimsDB:
    def __init__(self, own_VASP_address, compliance_key=None, client=None):
        self.own_VASP_address = LibraAddress.from_encoded_str(own_VASP_address).as_str()

        self.own_claim_DB = {}
        self.dyn_DB = {}
        self.reference_id_DB = {}
        self.checked_claims_DB = {}

        self.compliance_key = compliance_key
        self.client = client

    async def call_risk_function(self, originator_claim, beneficiary_claim, amount):
        return True

    async def generate_compliance_key_signature(self, originator_claim, beneficiary_claim, amount):
        # Find a unique_id that is not in use
        reference_id_random_part = urandom(16).hex()
        originator_vasp_address = originator_claim['vasp_libra_address']
        reference_id = f"{originator_vasp_address}_{reference_id_random_part}"
        origin_vasp = LibraAddress.from_encoded_str(originator_vasp_address)
        signature = self.compliance_key.sign_dual_attestation_data(reference_id, origin_vasp.onchain_address_bytes, amount).hex()

        # Save signature and bytes to remember travel rule information
        self.reference_id_DB[(reference_id, signature)] = (originator_claim, beneficiary_claim, amount)

        return (reference_id, signature)


    async def check_own_dynamic_subaddress(self, dynamic_subaddress):
        return deepcopy(self.dyn_DB.get(dynamic_subaddress, None))


    async def check_own_claim(self, claim):

        # First get the claim on record
        if claim['unique_identifier'] not in self.own_claim_DB:
            return Status.missing_identifier
        if 'verification_endpoint' not in claim:
            return Status.incorrect_record

        # Checking a claim means that it is a strict subset of the claim we have on record.
        our_claim = self.own_claim_DB[claim['unique_identifier']]
        dicts_to_check = [(claim, our_claim)]
        while dicts_to_check != []:
            given_struct, own_struct = dicts_to_check.pop()
            for field in given_struct:
                if type(given_struct[field]) in {int, str}:
                    if field not in own_struct:
                        return Status.unexpected_data
                    if given_struct[field] != own_struct[field]:
                        return Status.incorrect_record
                elif type(given_struct[field]) in {dict}:
                    if field not in own_struct:
                        return Status.unexpected_data
                    dicts_to_check += [(given_struct[field], own_struct[field])]
                else:
                    return Status.unexpected_data

        return Status.correct_record



    async def generate_dynamic_subaddress(self, beneficiary):
        # Find a unique_id that is not in use
        while True:
            fresh_subaddress = urandom(8)
            subaddress = LibraAddress.from_encoded_str(self.own_VASP_address)
            subaddress = LibraAddress.from_bytes(subaddress.onchain_address_bytes, subaddress_bytes = fresh_subaddress, hrp=subaddress.hrp)
            subaddress_str = subaddress.as_str()

            if subaddress_str not in self.dyn_DB:
                break

        self.dyn_DB[subaddress_str] = deepcopy(beneficiary)
        return (Status.fresh_dynamic_subaddress, subaddress_str)

    def add_own_claim(self, claim):
        # Find a unique_id that is not in use
        while True:
            unique_id = urandom(32).hex()
            if unique_id not in self.own_claim_DB:
                break

        # Update the claim with the unique identifier
        claim['unique_identifier'] = unique_id

        # Store the claim
        self.own_claim_DB[unique_id] = deepcopy(claim)

        # Return the claim
        return claim
