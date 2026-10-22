import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from intent_workbench.core import ModelError, evaluate, render_html, replay

ROOT=Path(__file__).resolve().parents[1]
class ReviewEdges(unittest.TestCase):
    def test_absent_expectation_remains_unscored(self):
        model=json.loads((ROOT/'fixtures/sharing-v1.json').read_text())
        result=replay(model,{'schema_version':1,'cases':[{'id':'not-reviewed','inputs':{}}]})
        self.assertEqual(result['cases'][0]['expectation_status'],'absent')
        self.assertEqual(result['cases'][0]['comparison'],'not_scored')

    def test_html_rejects_numeric_literals_javascript_cannot_represent(self):
        model={'schema_version':1,'id':'numbers','title':'Numbers','revision':'v1','inputs':[{'name':'size','type':'integer'}], 'outcomes':['allow'],'rules':[{'id':'large','when':{'size':{'eq':9007199254740993}},'outcome':'allow','review_status':'confirmed'}]}
        self.assertEqual(evaluate(model,{'size':9007199254740993})['status'],'resolved')
        with self.assertRaises(ModelError): render_html(model)

    def test_javascript_evaluator_handles_prototype_named_inputs(self):
        model=json.loads('{"schema_version":1,"id":"prototype","title":"Prototype","revision":"v1","inputs":[{"name":"__proto__","type":"boolean"}],"outcomes":["allow"],"rules":[{"id":"yes","when":{"__proto__":{"eq":true}},"outcome":"allow","review_status":"confirmed"}]}')
        inputs=json.loads('{"__proto__":true}')
        expected=evaluate(model,inputs)
        script='const {evaluateModel}=require(process.argv[1]); const [m,i]=JSON.parse(process.argv[2]); console.log(JSON.stringify(evaluateModel(m,i)));'
        result=subprocess.run(['node','-e',script,str(ROOT/'intent_workbench/workbench.js'),json.dumps([model,inputs])],text=True,capture_output=True,check=True)
        self.assertEqual(json.loads(result.stdout),expected)

    def test_cli_accepts_scalar_input_named_inputs(self):
        model={'schema_version':1,'id':'reserved-name','title':'Reserved name','revision':'v1','inputs':[{'name':'inputs','type':'boolean'}],'outcomes':['allow'],'rules':[{'id':'yes','when':{'inputs':{'eq':True}},'outcome':'allow','review_status':'confirmed'}]}
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder); model_path=base/'model.json'; input_path=base/'input.json'; output=base/'result.json'
            model_path.write_text(json.dumps(model)); input_path.write_text('{"inputs":true}')
            result=subprocess.run([sys.executable,'-m','intent_workbench','evaluate',str(model_path),'--input',str(input_path),'--out',str(output)],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(output.read_text())['outcome'],'allow')

    def test_cli_output_directory_and_resolved_input_aliases(self):
        with tempfile.TemporaryDirectory() as folder:
            base=Path(folder); model=ROOT/'fixtures/sharing-v2.json'; cases=ROOT/'fixtures/cases.json'
            model_bytes=model.read_bytes(); cases_bytes=cases.read_bytes()
            directory=base/'directory'; directory.mkdir()
            failed=subprocess.run([sys.executable,'-m','intent_workbench','build',str(model),'--out',str(directory)],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(failed.returncode,2); self.assertNotIn('Traceback',failed.stderr); self.assertIn('output',failed.stderr)
            model_alias=base/'model-alias.json'; model_alias.symlink_to(model)
            failed=subprocess.run([sys.executable,'-m','intent_workbench','build',str(model),'--out',str(model_alias)],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(failed.returncode,2); self.assertIn('overwrite input file',failed.stderr)
            cases_alias=base/'cases-alias.json'; cases_alias.symlink_to(cases)
            failed=subprocess.run([sys.executable,'-m','intent_workbench','replay',str(model),str(cases),'--out',str(cases_alias)],cwd=ROOT,text=True,capture_output=True)
            self.assertEqual(failed.returncode,2); self.assertIn('overwrite input file',failed.stderr)
            self.assertEqual(model.read_bytes(),model_bytes); self.assertEqual(cases.read_bytes(),cases_bytes)
