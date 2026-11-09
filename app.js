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
document.getElementById('run-ai').addEventListener('click',()=>{const model=document.getElementById('ai-model').value.trim();const data=document.getElementById('ai-data').value.trim();const epochs=document.getElementById('ai-epochs').value;const prompt=document.getElementById('ai-prompt').value.trim();if(!model||!data||data.startsWith('/')||data.includes('..')||data.includes('\\\\')||!prompt){alert('Проверь ID модели, относительный путь к JSONL и тестовый запрос.');return;}const url=repo+'/actions/workflows/train-ai.yml';window.open(url,'_blank','noopener');alert('На GitHub нажми Run workflow и укажи:\\nМодель: '+model+'\\nДанные: '+data+'\\nЭпохи: '+epochs+'\\nТестовый запрос: '+prompt);});
})();