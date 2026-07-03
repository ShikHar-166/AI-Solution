(function(){
  const navToggle=document.querySelector('.nav-toggle');
  const navLinks=document.querySelector('.nav-links');
  if(navToggle&&navLinks){navToggle.addEventListener('click',()=>navLinks.classList.toggle('open'));}

  const fab=document.getElementById('chatbotFab');
  const panel=document.getElementById('chatbotPanel');
  const closeBtn=document.getElementById('chatbotClose');
  const form=document.getElementById('chatbotForm');
  const input=document.getElementById('chatbotInput');
  const messages=document.getElementById('chatbotMessages');

  function addBubble(text,type){
    const div=document.createElement('div');
    div.className=type==='user'?'user-bubble':'bot-bubble';
    div.textContent=text;
    messages.appendChild(div);
    messages.scrollTop=messages.scrollHeight;
  }
  async function askBot(text){
    if(!text.trim()) return;
    addBubble(text,'user');
    input.value='';
    try{
      const res=await fetch('/api/chatbot/',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
      const data=await res.json();
      addBubble(data.answer||'Sorry, I could not understand that.','bot');
    }catch(e){addBubble('Connection error. Please try again.','bot');}
  }
  if(fab&&panel){fab.addEventListener('click',()=>panel.classList.toggle('open'));}
  if(closeBtn&&panel){closeBtn.addEventListener('click',()=>panel.classList.remove('open'));}
  if(form){form.addEventListener('submit',e=>{e.preventDefault();askBot(input.value);});}
  document.querySelectorAll('.chatbot-chips button').forEach(btn=>btn.addEventListener('click',()=>askBot(btn.dataset.question||btn.textContent)));
})();
