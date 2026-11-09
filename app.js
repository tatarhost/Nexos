(()=>{'use strict';
const repo='https://github.com/tatarhost/Nexos';
const views=[...document.querySelectorAll('.view')];
function show(name){views.forEach(v=>v.classList.toggle('active',v.id==='view-'+name));document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.view)));
document.querySelectorAll('[data-open]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.open)));
let target='android';
const names={android:'Android APK',java:'Java JAR',windows:'Windows EXE',minecraft:'Minecraft Mod'};
document.querySelectorAll('[data-target]').forEach(b=>b.addEventListener('click',()=>{target=b.dataset.target;document.querySelectorAll('[data-target]').forEach(x=>x.classList.toggle('selected',x===b));}));
document.getElementById('run-build').addEventListener('click',()=>{const path=document.getElementById('project-path').value.trim();if(!path||path.startsWith('/')||path.includes('..')||path.includes('\\')){alert('Укажи корректный относительный путь внутри репозитория.');return;}window.open(repo+'/actions/workflows/build.yml','_blank','noopener');alert('На странице GitHub нажми Run workflow и укажи:\nЦель: '+names[target]+'\nПапка проекта: '+path);});
document.getElementById('run-ai').addEventListener('click',()=>{const model=document.getElementById('ai-model').value.trim();const data=document.getElementById('ai-data').value.trim();const epochs=document.getElementById('ai-epochs').value;const prompt=document.getElementById('ai-prompt').value.trim();if(!model||!data||data.startsWith('/')||data.includes('..')||data.includes(String.fromCharCode(92))||!prompt){alert('Проверь ID модели, относительный путь к JSONL и тестовый запрос.');return;}const url=repo+'/actions/workflows/train-ai.yml';window.open(url,'_blank','noopener');alert('На GitHub нажми Run workflow и укажи:\\nРазмер модели: '+model+'\\nДанные: '+data+'\\nШаги обучения: '+epochs+'\\nТестовый запрос: '+prompt);});

const apiUrl=()=>document.getElementById('inference-url').value.trim().replace(/\/+$/,'');
const apiToken=()=>document.getElementById('inference-token').value.trim();
const inferenceStatus=document.getElementById('inference-status');
const modelSelect=document.getElementById('inference-model');
const messages=document.getElementById('inference-messages');
async function api(path,options={}) {
  const headers={...(options.headers||{}),Authorization:'Bearer '+apiToken()};
  const response=await fetch(apiUrl()+path,{...options,headers});
  const data=await response.json().catch(()=>({detail:'Сервер вернул некорректный ответ'}));
  if(!response.ok) throw new Error(data.detail||('HTTP '+response.status));
  return data;
}
function addMessage(role,text) {
  const item=document.createElement('div');
  item.className='chat-message '+role;
  const label=document.createElement('b');
  label.textContent=role==='user'?'ТЫ':'NEXUS AI';
  const body=document.createElement('p');
  body.textContent=text;
  item.append(label,body);
  messages.append(item);
  messages.scrollTop=messages.scrollHeight;
}
async function refreshModels() {
  const data=await api('/api/models');
  const previous=modelSelect.value;
  modelSelect.replaceChildren();
  for(const model of data.models) {
    const option=document.createElement('option');
    option.value=model.id;
    option.textContent=model.name+' · '+model.id;
    modelSelect.append(option);
  }
  if(previous&&data.models.some(m=>m.id===previous)) modelSelect.value=previous;
  if(!data.models.length) {
    const option=document.createElement('option');
    option.value='';
    option.textContent='Моделей пока нет — загрузи ZIP';
    modelSelect.append(option);
  }
  return data.models.length;
}
document.getElementById('inference-connect').addEventListener('click',async()=>{
  if(!apiUrl()||!apiToken()){alert('Укажи HTTPS URL сервера и API token.');return;}
  try {
    const health=await fetch(apiUrl()+'/health');
    if(!health.ok) throw new Error('Health check: HTTP '+health.status);
    await refreshModels();
    inferenceStatus.textContent='ПОДКЛЮЧЕНО · '+(await health.json()).device.toUpperCase();
    inferenceStatus.classList.add('connected');
  } catch(error) {inferenceStatus.textContent='ОШИБКА';inferenceStatus.classList.remove('connected');alert('Не удалось подключиться: '+error.message);}
});
document.getElementById('upload-model').addEventListener('click',async()=>{
  const file=document.getElementById('model-zip').files[0];
  if(!apiUrl()||!apiToken()){alert('Сначала подключи сервер и введи API token.');return;}
  if(!file||!file.name.toLowerCase().endsWith('.zip')){alert('Выбери ZIP-архив модели.');return;}
  const button=document.getElementById('upload-model');
  button.disabled=true;button.textContent='Загрузка…';
  try {
    const form=new FormData();form.append('file',file);
    const result=await api('/api/models/upload',{method:'POST',body:form});
    await refreshModels();modelSelect.value=result.id;
    inferenceStatus.textContent='МОДЕЛЬ ГОТОВА';
    alert('Модель загружена: '+result.name+' · '+Number(result.parameters).toLocaleString('ru-RU')+' параметров');
  } catch(error){alert('Ошибка загрузки: '+error.message);}
  finally{button.disabled=false;button.textContent='Загрузить ZIP';}
});
document.getElementById('send-inference').addEventListener('click',async()=>{
  const prompt=document.getElementById('inference-prompt').value.trim();
  const model_id=modelSelect.value;
  if(!apiUrl()||!apiToken()){alert('Сначала подключи сервер.');return;}
  if(!model_id){alert('Сначала загрузи ZIP модели и выбери её.');return;}
  if(!prompt)return;
  addMessage('user',prompt);
  document.getElementById('inference-prompt').value='';
  const button=document.getElementById('send-inference');
  button.disabled=true;button.textContent='Думаю…';
  try {
    const result=await api('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({model_id,prompt,max_new_tokens:160})});
    addMessage('assistant',result.answer||'(Модель вернула пустой ответ)');
  } catch(error){addMessage('assistant','Ошибка: '+error.message);}
  finally{button.disabled=false;button.textContent='Отправить ↗';}
});
document.getElementById('inference-prompt').addEventListener('keydown',event=>{
  if(event.key==='Enter'&&!event.shiftKey){event.preventDefault();document.getElementById('send-inference').click();}
});
})();