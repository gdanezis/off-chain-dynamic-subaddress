from service import *

import pytest
from libra_address import LibraAddress
from crypto import ComplianceKey

def fixture_example_claim(port):
    vasp_bytes = urandom(16)
    vasp_sub_bytes   = urandom(8)
    vasp_address = LibraAddress.from_bytes(vasp_bytes).as_str()
    vasp_subaddress = LibraAddress.from_bytes(vasp_bytes, vasp_sub_bytes).as_str()

    originator_claim = {
        'legal_name' : 'Adam Smith',
        'long_term_subaddress': vasp_subaddress,
        'vasp_name' : 'Example VASP inc.',
        'vasp_libra_address': vasp_address,
        'issue_date': '2020-01-18',
        'expiry_date': '2022-01-18',
        'unique_identifier' : None,
        'bindings': {'phone-1': '+1-465-883772', 'email-1': 'adam@smith.com'},
        'originator_data' : {
            'date_of_birth' : '1958-04-22',
            'place_of_birth': 'United Kingdom',
            'identity': {'passport_number': '77tjjjr774'}
        },
        'verification_endpoint' : f'http://localhost:{port}',
    }
    beneficiary_claim = {
        'legal_name' : 'Adam Smith',
        'long_term_subaddress': vasp_subaddress,
        'vasp_name' : 'Example VASP inc.',
        'vasp_libra_address': vasp_address,
        'issue_date': '2020-01-18',
        'expiry_date': '2022-01-18',
        'unique_identifier' : None,
        'verification_endpoint' : f'http://localhost:{port}',
    }

    return (vasp_address, vasp_subaddress, originator_claim, beneficiary_claim)

def fixture_example_claim_another(port):
    vasp_bytes = urandom(16)
    vasp_sub_bytes   = urandom(8)
    vasp_address = LibraAddress.from_bytes(vasp_bytes).as_str()
    vasp_subaddress = LibraAddress.from_bytes(vasp_bytes, vasp_sub_bytes).as_str()

    originator_claim = {
        'legal_name' : 'Angela Smith',
        'long_term_subaddress': vasp_subaddress,
        'vasp_name' : 'Another VASP inc.',
        'vasp_libra_address': vasp_address,
        'issue_date': '2020-06-20',
        'expiry_date': '2022-07-01',
        'unique_identifier' : None,
        'bindings': {'phone-1': '+1-465-123456', 'email-1': 'angela@smith.com'},
        'originator_data' : {
            'date_of_birth' : '1956-08-05',
            'place_of_birth': 'United Kingdom',
            'identity': {'passport_number': 'h766ghjk'}
        },
        'verification_endpoint' : f'http://localhost:{port}',
    }
    beneficiary_claim = {
        'legal_name' : 'Angela Smith',
        'long_term_subaddress': vasp_subaddress,
        'vasp_name' : 'Another VASP inc.',
        'vasp_libra_address': vasp_address,
        'issue_date': '2020-06-20',
        'expiry_date': '2022-07-01',
        'unique_identifier' : None,
        'verification_endpoint' : f'http://localhost:{port}',
    }

    return (vasp_address, vasp_subaddress, originator_claim, beneficiary_claim)


@pytest.mark.asyncio
async def test_run_service_with_db():
    port = 8080
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)
    cdb = ClaimsDB(vasp_address)
    runner = await run_service(cdb, port=port)
    await runner.cleanup()

@pytest.mark.asyncio
async def test_run_service_add_claim():
    port=8082
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)

    cdb = ClaimsDB(vasp_address)
    runner = await run_service(cdb, port=port)

    originator_claim = cdb.add_own_claim(originator_claim)

    client = DynClient()
    status = await client.check_other_claim(originator_claim)
    assert status == Status.correct_record

    await runner.cleanup()

@pytest.mark.asyncio
async def test_run_service_check_partial():
    port=8083
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)

    cdb = ClaimsDB(vasp_address)
    runner = await run_service(cdb, port=port)

    claim = cdb.add_own_claim(originator_claim)
    beneficiary_claim['unique_identifier'] = claim['unique_identifier']

    client = DynClient()
    status = await client.check_other_claim(beneficiary_claim)
    assert status == Status.correct_record

    await runner.cleanup()

@pytest.mark.asyncio
async def test_run_service_check_incorrect():
    port = 8084
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)

    cdb = ClaimsDB(vasp_address)
    runner = await run_service(cdb, port=port)

    claim = cdb.add_own_claim(originator_claim)
    beneficiary_claim['unique_identifier'] = claim['unique_identifier']

    # Change the name
    beneficiary_claim['legal_name'] = 'Other Name'

    client = DynClient()
    status = await client.check_other_claim(beneficiary_claim)
    assert status == Status.incorrect_record

    await runner.cleanup()


@pytest.mark.asyncio
async def test_run_service_get_dynamic():
    port=8085
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)

    cdb = ClaimsDB(vasp_address)
    runner = await run_service(cdb, port=port)

    claim = cdb.add_own_claim(originator_claim)
    beneficiary_claim['unique_identifier'] = claim['unique_identifier']

    client = DynClient()
    status, dynamic_subaddress = await client.get_subaddress_from_beneficiary_claim(beneficiary_claim)
    assert status == Status.fresh_dynamic_subaddress

    await runner.cleanup()

@pytest.mark.asyncio
async def test_run_service_get_dynamic_bad_input():
    port=8086
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)

    cdb = ClaimsDB(vasp_address)
    runner = await run_service(cdb, port=port)

    claim = cdb.add_own_claim(originator_claim)
    beneficiary_claim['unique_identifier'] = claim['unique_identifier']

    # Change the name
    beneficiary_claim['legal_name'] = 'Other Name'

    client = DynClient()
    status, dynamic_subaddress = await client.get_subaddress_from_beneficiary_claim(beneficiary_claim)
    assert status == Status.incorrect_record

    await runner.cleanup()

@pytest.mark.asyncio
async def test_run_service_get_dynamic_from_dynamic():
    port=8087
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)

    cdb = ClaimsDB(vasp_address)
    runner = await run_service(cdb, port=port)

    claim = cdb.add_own_claim(originator_claim)
    beneficiary_claim['unique_identifier'] = claim['unique_identifier']

    client = DynClient()
    status, dynamic_subaddress = await client.get_subaddress_from_beneficiary_claim(beneficiary_claim)
    assert status == Status.fresh_dynamic_subaddress

    status2, dynamic_subaddress2 = await client.get_subaddress_from_subaddress(f'http://localhost:{port}', dynamic_subaddress)
    assert status2 == Status.fresh_dynamic_subaddress
    assert dynamic_subaddress != dynamic_subaddress2

    assert await cdb.check_own_dynamic_subaddress(dynamic_subaddress) == beneficiary_claim
    assert await cdb.check_own_dynamic_subaddress(dynamic_subaddress2) == beneficiary_claim

    await runner.cleanup()

@pytest.mark.asyncio
async def test_run_service_get_dynamic_bad_input():
    port=8086
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)

    cdb = ClaimsDB(vasp_address)
    runner = await run_service(cdb, port=port)

    claim = cdb.add_own_claim(originator_claim)
    beneficiary_claim['unique_identifier'] = claim['unique_identifier']

    # Change the name
    beneficiary_claim['legal_name'] = 'Other Name'

    client = DynClient()
    status, dynamic_subaddress = await client.get_subaddress_from_beneficiary_claim(beneficiary_claim)
    assert status == Status.incorrect_record

    await runner.cleanup()

@pytest.mark.asyncio
async def test_run_service_attest():

    vasp_bytes = urandom(16)
    vasp_sub_bytes   = urandom(8)
    vasp_address = LibraAddress.from_bytes(vasp_bytes).as_str()
    vasp_subaddress = LibraAddress.from_bytes(vasp_bytes, vasp_sub_bytes).as_str()

    # Run VASP 1
    port=8087
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)
    client = DynClient()
    cdb = ClaimsDB(vasp_address, compliance_key=ComplianceKey.generate(), client=client)
    runner = await run_service(cdb, port=port)

    claim = cdb.add_own_claim(originator_claim)
    beneficiary_claim['unique_identifier'] = claim['unique_identifier']


    # Run VASP 2
    port2=8088
    vasp_address2, vasp_subaddress2, originator_claim2, beneficiary_claim2 = fixture_example_claim_another(port2)
    cdb2 = ClaimsDB(vasp_address2, compliance_key=ComplianceKey.generate())
    runner2 = await run_service(cdb2, port=port2)

    originator_claim2 = cdb2.add_own_claim(originator_claim2)

    client_other = DynClient()
    status, reference_id, signature = await client_other.get_attestation(originator_claim2, beneficiary_claim, 1000)
    assert status == Status.compliance_signature

    await runner.cleanup()
    await runner2.cleanup()

@pytest.mark.asyncio
async def test_run_service_attest_bad_beneficiary():

    vasp_bytes = urandom(16)
    vasp_sub_bytes   = urandom(8)
    vasp_address = LibraAddress.from_bytes(vasp_bytes).as_str()
    vasp_subaddress = LibraAddress.from_bytes(vasp_bytes, vasp_sub_bytes).as_str()

    # Run VASP 1
    port=8087
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)
    client = DynClient()
    cdb = ClaimsDB(vasp_address, compliance_key=ComplianceKey.generate(), client=client)
    runner = await run_service(cdb, port=port)

    claim = cdb.add_own_claim(originator_claim)
    beneficiary_claim['unique_identifier'] = claim['unique_identifier']
    beneficiary_claim['legal_name'] = 'Wrong Name'


    # Run VASP 2
    port2=8088
    vasp_address2, vasp_subaddress2, originator_claim2, beneficiary_claim2 = fixture_example_claim_another(port2)
    cdb2 = ClaimsDB(vasp_address2, compliance_key=ComplianceKey.generate())
    runner2 = await run_service(cdb2, port=port2)

    originator_claim2 = cdb2.add_own_claim(originator_claim2)

    client_other = DynClient()
    status = await client_other.get_attestation(originator_claim2, beneficiary_claim, 1000)
    assert status == Status.incorrect_record

    await runner.cleanup()
    await runner2.cleanup()

@pytest.mark.asyncio
async def test_run_service_attest_bad_originator():

    vasp_bytes = urandom(16)
    vasp_sub_bytes   = urandom(8)
    vasp_address = LibraAddress.from_bytes(vasp_bytes).as_str()
    vasp_subaddress = LibraAddress.from_bytes(vasp_bytes, vasp_sub_bytes).as_str()

    # Run VASP 1
    port=8087
    vasp_address, vasp_subaddress, originator_claim, beneficiary_claim = fixture_example_claim(port)
    client = DynClient()
    cdb = ClaimsDB(vasp_address, compliance_key=ComplianceKey.generate(), client=client)
    runner = await run_service(cdb, port=port)

    claim = cdb.add_own_claim(originator_claim)
    beneficiary_claim['unique_identifier'] = claim['unique_identifier']

    # Run VASP 2
    port2=8088
    vasp_address2, vasp_subaddress2, originator_claim2, beneficiary_claim2 = fixture_example_claim_another(port2)
    cdb2 = ClaimsDB(vasp_address2, compliance_key=ComplianceKey.generate())
    runner2 = await run_service(cdb2, port=port2)

    originator_claim2 = cdb2.add_own_claim(originator_claim2)
    originator_claim2['legal_name'] = 'Wrong Name'

    client_other = DynClient()
    status = await client_other.get_attestation(originator_claim2, beneficiary_claim, 1000)
    assert status == Status.incorrect_originator_record

    await runner.cleanup()
    await runner2.cleanup()
