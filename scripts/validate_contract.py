import json, pathlib, sys, hashlib
from jsonschema import Draft202012Validator
ROOT=pathlib.Path(__file__).resolve().parents[1]
def validate(pack, root=None):
    schema=json.loads((ROOT/'contracts/garden-pack.schema.json').read_text())
    Draft202012Validator(schema).validate(pack)
    runs={r['id']:r for r in pack['runs']}
    assert len(runs)==len(pack['runs']), 'duplicate run ID'
    assert len({a['id'] for a in pack['assets']})==len(pack['assets']), 'duplicate asset ID'
    synthetic=pack['evidenceMode']=='synthetic'
    for r in runs.values():
        assert (r['jobId'] is None) if synthetic else bool(r['jobId']), 'evidence/job mismatch'
        assert not(synthetic and r['execution']=='hardware'), 'synthetic hardware claim'
    for a in pack['assets']:
        assert all(x in runs for x in a['sourceRunIds']), 'unknown run'
        assert synthetic or a['sourceRunIds'], 'Atlas asset missing contributing run'
        p=pathlib.PurePosixPath(a['path'])
        assert not p.is_absolute() and '..' not in p.parts and ':' not in a['path'], 'unsafe path'
        if root is not None:
            base=pathlib.Path(root).resolve(); f=(base/a['path']).resolve()
            assert f.is_relative_to(base), 'symlink escape'
            assert hashlib.sha256(f.read_bytes()).hexdigest()==a['sha256'], 'asset hash mismatch'
    return True
if __name__=='__main__':
    if len(sys.argv)>1:
        f=pathlib.Path(sys.argv[1]); validate(json.loads(f.read_text()),f.parent)
        print('Pack structure, references, paths and hashes valid; provenance truth requires release review.')
    else:
        import unittest, copy, tempfile
        class Checks(unittest.TestCase):
            def setUp(self):
                h=hashlib.sha256(b'development fixture').hexdigest()
                self.p={'schemaVersion':1,'id':'synthetic-test','producer':'contract-test','evidenceMode':'synthetic','mothbakeCommit':'b36ac00286f63c3ee4d57a632fb8909c2d189f72','assets':[{'id':'a','role':'test','path':'fixture.txt','mime':'text/plain','sha256':h,'sourceRunIds':['r']}],'runs':[{'id':'r','engineId':'synthetic-fixture','execution':'unknown','parameters':{},'inputSha256':[],'outputSha256':[h],'jobId':None}]}
            def test_valid(self): self.assertTrue(validate(self.p))
            def test_real_requires_job(self):
                self.p['evidenceMode']='atlas-live'
                with self.assertRaises(AssertionError): validate(self.p)
            def test_synthetic_not_hardware(self):
                self.p['runs'][0]['execution']='hardware'
                with self.assertRaises(AssertionError): validate(self.p)
            def test_traversal(self):
                self.p['assets'][0]['path']='../bad'
                with self.assertRaises(Exception): validate(self.p)
            def test_reference(self):
                self.p['assets'][0]['sourceRunIds']=['missing']
                with self.assertRaises(AssertionError): validate(self.p)
            def test_hash(self):
                with tempfile.TemporaryDirectory() as t:
                    pathlib.Path(t,'fixture.txt').write_bytes(b'development fixture'); self.assertTrue(validate(self.p,t))
                    pathlib.Path(t,'fixture.txt').write_bytes(b'changed')
                    with self.assertRaises(AssertionError): validate(self.p,t)
            def test_schema(self):
                self.p['secret']='forbidden-field'
                with self.assertRaises(Exception): validate(self.p)
        unittest.main()
