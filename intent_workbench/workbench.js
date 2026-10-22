(() => {
  'use strict';
  function evaluateModel(model, inputs) {
    const matched=[], unknown=[], missing=new Set(), results=[];
    for(const rule of model.rules){
      const conditions=[],ruleMissing=[];let sawUnknown=false,sawFalse=false;
      for(const [name,condition] of Object.entries(rule.when)){
        let state,detail;
        if(!Object.prototype.hasOwnProperty.call(inputs,name)){state='unknown';detail=`${name} is missing`;sawUnknown=true;ruleMissing.push(name);}
        else {const value=inputs[name], [op,expected]=Object.entries(condition)[0];let ok;
          if(op==='eq')ok=value===expected;
          else if(op==='in')ok=expected.includes(value);
          else if(op==='gte')ok=value>=expected;
          else ok=value<=expected;
          state=ok?'match':'no_match';sawFalse ||= !ok;
          detail=op==='eq'?(ok?`${name} equals ${JSON.stringify(expected)}`:`${name} is ${JSON.stringify(value)}, expected ${JSON.stringify(expected)}`):op==='in'?(ok?`${name} is in the listed values`:`${name} is not in the listed values`):op==='gte'?(ok?`${name} is at least ${expected}`:`${name} is below ${expected}`):(ok?`${name} is at most ${expected}`:`${name} is above ${expected}`);
        }
        conditions.push({input:name,state,detail});
      }
      const state=sawFalse?'no_match':sawUnknown?'unknown':'match';
      if(state==='match')matched.push(rule);else if(state==='unknown'){unknown.push(rule.id);for(const name of ruleMissing)missing.add(name);}
      results.push({rule_id:rule.id,state,outcome:rule.outcome,conditions});
    }
    let status,outcome=null;
    if(unknown.length)status='missing';
    else {const outcomes=[...new Set(matched.map(x=>x.outcome))];if(!outcomes.length)status='unresolved';else if(outcomes.length>1)status='conflict';else{status='resolved';outcome=outcomes[0];}}
    return {status,outcome,matched_rule_ids:matched.map(x=>x.id),unknown_rule_ids:unknown,missing_inputs:[...missing].sort(),rule_results:results,prediction_label:'model prediction'};
  }
  if(typeof module!=='undefined' && module.exports) module.exports={evaluateModel};
  if(typeof document==='undefined') return;
  const model=JSON.parse(document.getElementById('model-data').textContent);
  const fields=document.getElementById('fields'), rulesEl=document.getElementById('rules');
  const inputValues=Object.create(null);
  const pretty=s=>s.replaceAll('_',' ');
  for(const spec of model.inputs){
    const label=document.createElement('label');label.className='field';label.textContent=pretty(spec.name);
    let control;
    if(spec.type==='enum'||spec.type==='boolean'){
      control=document.createElement('select');control.append(new Option('Unset — unknown',''));
      const values=spec.type==='boolean'?[['true','Yes'],['false','No']]:spec.values.map(value=>[value,value]);
      for(const [value,name] of values)control.append(new Option(name,value));
    } else {control=document.createElement('input');control.type='number';control.step='1';control.placeholder='Unset';if(spec.minimum!==undefined)control.min=String(spec.minimum);if(spec.maximum!==undefined)control.max=String(spec.maximum);}
    control.id=`input-${spec.name}`;control.name=spec.name;
    const hint=document.createElement('span');hint.className='hint';hint.textContent=spec.type==='integer'?'Whole number; leave blank when unknown':'Choose a value or leave unset';
    const error=document.createElement('span');error.className='field-error';error.id=`error-${spec.name}`;error.setAttribute('aria-live','polite');control.setAttribute('aria-describedby',error.id);
    label.append(control,hint,error);fields.append(label);inputValues[spec.name]=control;
    control.addEventListener('input',update);control.addEventListener('change',update);
  }
  function collect(){const inputs=Object.create(null),errors=[];
    for(const spec of model.inputs){const el=inputValues[spec.name],raw=el.value;let message='';
      if(raw===''){delete inputs[spec.name];}
      else if(spec.type==='boolean')inputs[spec.name]=raw==='true';
      else if(spec.type==='integer'){const value=Number(raw);if(!Number.isSafeInteger(value))message='Enter a whole number within the supported numeric range.';else if(spec.minimum!==undefined&&value<spec.minimum)message=`Use ${spec.minimum} or higher.`;else if(spec.maximum!==undefined&&value>spec.maximum)message=`Use ${spec.maximum} or lower.`;else inputs[spec.name]=value;}
      else inputs[spec.name]=raw;
      const err=document.getElementById(`error-${spec.name}`);err.textContent=message;if(message){el.setAttribute('aria-invalid','true');errors.push(message);}else el.removeAttribute('aria-invalid');
    }return {inputs,errors};
  }
  function update(){const {inputs,errors}=collect();if(errors.length){document.getElementById('verdict-status').textContent='Invalid input';document.getElementById('verdict-outcome').textContent='Correct the marked value';document.getElementById('missing').textContent='';rulesEl.replaceChildren();return;}
    const result=evaluateModel(model,inputs);const status=document.getElementById('verdict-status');status.textContent=result.status;status.dataset.status=result.status;document.getElementById('verdict-outcome').textContent=result.outcome||({missing:'Decision needed',conflict:'Rules disagree',unresolved:'No rule applies'}[result.status]);
    document.getElementById('missing').textContent=result.missing_inputs.length?`Missing facts: ${result.missing_inputs.map(pretty).join(', ')}`:'';
    document.getElementById('rule-count').textContent=`${result.matched_rule_ids.length} match · ${result.unknown_rule_ids.length} unknown`;
    const byId=new Map(model.rules.map(rule=>[rule.id,rule]));
    const rows=result.rule_results.map(row=>{const box=document.createElement('div');box.className=`rule-row state-${row.state}`;const name=document.createElement('span');name.className='rule-name';name.textContent=row.rule_id;const details=document.createElement('span');details.className='rule-conditions';if(row.conditions.length){for(const condition of row.conditions){const line=document.createElement('span');line.textContent=`${pretty(condition.input)}: ${condition.detail}`;details.append(line);}}else details.textContent='Always matches';const outcome=document.createElement('span');outcome.className='rule-outcome';outcome.textContent=byId.get(row.rule_id).outcome;box.append(name,details,outcome);return box;});rulesEl.replaceChildren(...rows);
  }
  document.getElementById('reset').addEventListener('click',()=>{for(const el of Object.values(inputValues))el.value='';update();inputValues[model.inputs[0]?.name]?.focus();});
  document.getElementById('download').addEventListener('click',()=>{const {inputs,errors}=collect();if(errors.length)return;const prediction=evaluateModel(model,inputs);const payload={schema_version:1,model_id:model.id,revision:model.revision,inputs,prediction,expected:null,review_status:'unconfirmed'};const blob=new Blob([JSON.stringify(payload,null,2)+'\n'],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download=`${model.id}-${model.revision}-case.json`;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  update();
})();
