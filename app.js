(()=>{'use strict';
const repo='https://github.com/tatarhost/Nexos';
const views=[...document.querySelectorAll('.view')];
function show(name){views.forEach(v=>v.classList.toggle('active',v.id==='view-'+name));document.querySelectorAll('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));}
document.querySelectorAll('[data-view]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.view)));
document.querySelectorAll('[data-open]').forEach(b=>b.addEventListener('click',()=>show(b.dataset.open)));
let target='android';
document.querySelectorAll('[data-target]').forEach(b=>b.addEventListener('click',()=>{target=b.dataset.target;document.querySelectorAll('[data-target]').forEach(x=>x.classList.toggle('selected',x===b));}));
document.getElementById('run-build').addEventListener('click',()=>{const path=document.getElementById('project-path').value.trim();if(!path||path.startsWith('/')||path.includes('..')||path.includes('\\')){alert('Укажи корректный относительный путь внутри репозитория.');return;}window.open(repo+'/actions/workflows/build.yml','_blank','noopener');});
})();