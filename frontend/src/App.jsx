import React, { useEffect, useRef, useState, Suspense, lazy } from 'react';
import { ArrowUp, ArrowUpRight, AudioLines, Mic, MessageSquare, Plus, Sparkles, Search, Code2, Brain, X, ShieldCheck, Volume2, VolumeX, Trash2 } from 'lucide-react';
import './style.css';
import { auth } from './auth';
const Orb=lazy(()=>import('./Orb'));
const API=(import.meta.env.VITE_API_URL||'').replace(/\/$/,'');
const suggestions=[{icon:Sparkles,title:'Make something click',sub:'Break down a complex idea',prompt:'Explain how neural networks learn, with a simple analogy.'},{icon:Code2,title:'Build your next idea',sub:'Create a Python starting point',prompt:'Create a Python file for a command-line to-do list.'},{icon:Brain,title:'Keep a thought close',sub:'Save a note for later',prompt:'Take a note to explore my next big idea this weekend.'},{icon:Search,title:'Follow your curiosity',sub:'Find something worth exploring',prompt:'Search YouTube for creative coding with Three.js'}];
export default function App(){
 const [token,setToken]=useState('');const [account,setAccount]=useState(null);const [login,setLogin]=useState(false);const [loginBusy,setLoginBusy]=useState(false);const [authReady,setAuthReady]=useState(false);const [modelStatus,setModelStatus]=useState('');
 const [historyLoading,setHistoryLoading]=useState(false);const [input,setInput]=useState('');const [messages,setMessages]=useState([]);const [busy,setBusy]=useState(false);const [listening,setListening]=useState(false);const [speaking,setSpeaking]=useState(false);const [voice,setVoice]=useState(false);const [error,setError]=useState('');const [online,setOnline]=useState(false);const [panel,setPanel]=useState(false);
 const recognition=useRef(null), bottom=useRef(null), activeAccount=useRef(null), requestController=useRef(null);
 useEffect(()=>{
  localStorage.removeItem('nova-token');
  if(!auth){setAuthReady(true);return}
  let alive=true;
  function apply(session){
   if(!alive)return;
   const id=session?.user?.id||null;
   if(activeAccount.current!==id){requestController.current?.abort();recognition.current?.abort();window.speechSynthesis?.cancel();setSpeaking(false);setListening(false);setBusy(false);setMessages([]);setError('');setInput('');setModelStatus('');activeAccount.current=id}
   setToken(session?.access_token||'');setAccount(session?.user||null);setAuthReady(true);
   if(session){setLogin(false);}
  }
  const {data:{subscription}}=auth.auth.onAuthStateChange((_event,session)=>apply(session));
  auth.auth.getSession().then(({data,error})=>{if(error){if(alive){setError('Sign-in could not be restored. Please sign in again.');setAuthReady(true)}}else apply(data.session)});
  return ()=>{alive=false;subscription.unsubscribe();requestController.current?.abort()};
 },[]);
 useEffect(()=>{
  if(!account){setHistoryLoading(false);return}
  setHistoryLoading(true);let alive=true;
  request('/api/history').then(data=>{if(alive)setMessages(data.messages)}).catch(e=>{if(alive)setError(e.message)}).finally(()=>{if(alive)setHistoryLoading(false)});
  request('/api/model-status').then(data=>{if(alive)setModelStatus(data.message)}).catch(e=>{if(alive)setModelStatus(e.message)});
  return ()=>{alive=false};
 },[account?.id]);
 useEffect(()=>{fetch(API+'/healthz',{signal:AbortSignal.timeout(10000)}).then(r=>setOnline(r.ok)).catch(()=>setOnline(false));return ()=>{recognition.current?.abort();window.speechSynthesis?.cancel();}},[]);
 useEffect(()=>{bottom.current?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth'});},[messages,busy]);
 async function request(path,options={}){
  const owner=activeAccount.current;
  const {data,error}=auth?await auth.auth.getSession():{data:{session:null}};
  if(error||!data.session){setLogin(true);throw Error('Please sign in with your email.')}
  if(owner!==data.session.user.id||activeAccount.current!==owner)throw new DOMException('Account changed','AbortError');
  const r=await fetch(API+path,{...options,headers:{'Content-Type':'application/json',Authorization:`Bearer ${data.session.access_token}`},signal:options.signal||AbortSignal.timeout(75000)});
  if(activeAccount.current!==data.session.user.id)throw new DOMException('Account changed','AbortError');
  let result;try{result=await r.json()}catch{throw Error('The server is temporarily unavailable. Please try again.')}
  if(!r.ok){if(r.status===401){await auth.auth.signOut({scope:'local'});setLogin(true)}throw Error(typeof result.detail==='string'?result.detail:'Please check your request and try again.')}
  return result;
 }
 async function connect(e){
  e.preventDefault();setLoginBusy(true);setError('');
  try{
   if(!auth)throw Error('Google sign-in is being set up. Please try again later.');
   const {error}=await auth.auth.signInWithOAuth({provider:'google',options:{redirectTo:window.location.origin+'/'}});
   if(error)throw error;
  }catch(e){setError(e.message)}finally{setLoginBusy(false)}
 }
 async function disconnect(){
  const {error}=await auth.auth.signOut({scope:'local'});
  if(error){setError('Could not sign out. Please try again.');return}
  setPanel(false);
 }
 async function send(text=input){if(!text.trim()||busy||listening||historyLoading)return;if(!authReady)return;if(!token){setInput(text);setLogin(true);return}window.speechSynthesis?.cancel();setSpeaking(false);setInput('');setError('');setMessages(m=>[...m,{role:'user',text}]);setBusy(true);const owner=activeAccount.current;const controller=new AbortController();requestController.current=controller;try{const data=await request('/api/chat',{method:'POST',signal:AbortSignal.any([controller.signal,AbortSignal.timeout(75000)]),body:JSON.stringify({text,timezone:Intl.DateTimeFormat().resolvedOptions().timeZone})});if(activeAccount.current!==owner)return;setMessages(m=>[...m,{role:'assistant',...data}]);setOnline(true);if(voice&&window.speechSynthesis){const speech=new SpeechSynthesisUtterance(data.text.slice(0,700));speech.onstart=()=>setSpeaking(true);speech.onend=speech.onerror=()=>setSpeaking(false);window.speechSynthesis.speak(speech)}}catch(e){if(activeAccount.current!==owner||e.name==='AbortError')return;setError(e.name==='TimeoutError'?'Nova took too long to respond. Please try again.':e.message)}finally{if(activeAccount.current===owner)setBusy(false)}}
 function mic(){if(listening){recognition.current?.stop();return}const Speech=window.SpeechRecognition||window.webkitSpeechRecognition;if(!window.isSecureContext){setError('Microphone access requires HTTPS or localhost.');return}if(!Speech){setError('Voice recognition is unavailable in this browser. You can type your message instead.');return}if(!token){setLogin(true);return}window.speechSynthesis?.cancel();setSpeaking(false);setError('');const r=new Speech();recognition.current=r;r.lang='en-US';r.interimResults=true;r.onresult=e=>setInput(Array.from(e.results).map(x=>x[0].transcript).join(' '));r.onerror=e=>{setError(e.error==='not-allowed'?'Microphone permission was denied. Allow it in your browser settings.':'Voice input stopped: '+e.error);setListening(false)};r.onend=()=>setListening(false);try{r.start();setListening(true)}catch{setListening(false);setError('Could not start the microphone. Please try again.')}}
 function download(action){const url=URL.createObjectURL(new Blob([action.content],{type:'text/x-python'}));const a=document.createElement('a');a.href=url;a.download='nova_generated.py';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}
 async function erase(){if(!window.confirm('Delete all notes, memories, and model conversation stored for your account?'))return;try{await request('/api/data',{method:'DELETE'});setMessages([]);setPanel(false)}catch(e){setError(e.message)}}
 return <div className="shell"><aside className="rail"><a className="brand" href="#" aria-label="Nova home"><AudioLines size={25}/></a><button className="rail-btn selected" title="Assistant" aria-label="Assistant" onClick={()=>setPanel(false)}><MessageSquare size={20}/></button><button className="rail-btn" title="New view" aria-label="Clear visible conversation" disabled={busy||listening||historyLoading} onClick={()=>{setMessages([]);setError('')}}><Plus size={22}/></button><div className="rail-bottom"><button className="avatar" title="Privacy and session" aria-label="Privacy and session" onClick={()=>setPanel(!panel)}>N</button></div></aside>
 <main><header><a href="#" className="wordmark">nova<span> / </span><small>PERSONAL INTELLIGENCE</small></a><div className="header-right"><span className="connection"><i className={online?'on':''}/>{online?'API online':'API offline'}</span><button className="connect" onClick={()=>token?setPanel(!panel):setLogin(true)}>{token?'Your workspace':'Sign in'}<ArrowUpRight size={14}/></button></div></header>
 <div className="workspace"><section className={'hero '+(messages.length?'compact':'')}><div className="eyebrow"><span/> A LITTLE SPACE FOR BIG IDEAS</div><h1>Your ideas,<br/><em>amplified.</em></h1><p>Think out loud. Find a new direction.<br/>Make everyday things a little more extraordinary.</p><div className="orb-wrap"><div className="orb-glow"/><Suspense fallback={<div className="fallback-orb"/>}><Orb active={listening||speaking||busy}/></Suspense><div className="orb-caption"><span className={busy||listening?'pulse':''}/>{listening?'Listening to you':busy?'Connecting the dots':speaking?'Speaking':'Ready when you are'}</div></div></section>
 {messages.length===0?<section className="starters"><div className="section-label">WHERE SHALL WE START?<span>Pick a thought. Or bring your own.</span></div><div className="cards">{suggestions.map(({icon:Icon,title,sub,prompt})=><button key={title} className="card" onClick={()=>send(prompt)} disabled={busy||historyLoading||!authReady}><Icon size={21}/><ArrowUpRight size={15} className="card-arrow"/><strong>{title}</strong><span>{sub}</span></button>)}</div></section>:<section className="conversation" aria-label="Conversation" aria-live="polite">{messages.map((m,i)=><article key={i} className={'message '+m.role}><div className="speaker">{m.role==='assistant'?<AudioLines size={16}/>:<span>Y</span>}{m.role==='assistant'?'NOVA':'YOU'}</div><p>{m.text}</p>{m.action?.type==='link'&&/^https:\/\//.test(m.action.url)&&<a className="action" href={m.action.url} target="_blank" rel="noopener noreferrer">{m.action.label}<ArrowUpRight size={14}/></a>}{m.action?.type==='download'&&<button className="action" onClick={()=>download(m.action)}>Download Python file<Code2 size={14}/></button>}</article>)}{busy&&<div className="thinking">Nova is thinking<span>•••</span></div>}<div ref={bottom}/></section>}
 <section className="composer-wrap">{error&&<div className="error" role="alert">{error}<button aria-label="Dismiss error" onClick={()=>setError('')}><X size={15}/></button></div>}<form className="composer" onSubmit={e=>{e.preventDefault();send()}}><AudioLines className="input-icon" size={23}/><input aria-label="Message Nova" value={input} maxLength={4000} onChange={e=>setInput(e.target.value)} placeholder={listening?'Listening… review your words, then send.':'Ask anything, or just start talking…'} disabled={busy}/><button type="button" className={listening?'mic live':'mic'} aria-label={listening?'Stop microphone':'Start microphone'} onClick={mic} disabled={busy}><Mic size={19}/></button><button className="send" aria-label="Send message" disabled={busy||listening||historyLoading||!authReady||!input.trim()}><ArrowUp size={20}/></button></form><div className="composer-footer"><span><ShieldCheck size={13}/> Your keys stay on the server</span><button onClick={()=>{setVoice(!voice);window.speechSynthesis?.cancel();setSpeaking(false)}}>{voice?<Volume2 size={14}/>:<VolumeX size={14}/>}Voice replies {voice?'on':'off'}</button></div><p className="voice-note">Voice recognition may use your browser’s speech service. Review the transcript before sending.</p></section></div><footer><span>NOVA / YOUR PERSONAL AI WORKSPACE</span><span>Built for the way you think.</span></footer></main>
 {panel&&<div className="shade" onClick={()=>setPanel(false)}><section className="modal" onClick={e=>e.stopPropagation()}><button className="close" aria-label="Close" onClick={()=>setPanel(false)}><X/></button><ShieldCheck className="mint"/><h2>Your workspace.</h2><p>Signed in as {account?.email}. Your notes, memories, and conversations belong to your account and are available when you sign in again. Each collection keeps up to 100 entries.</p><p>“New view” clears only the visible chat. Signing out keeps your saved data. Use “Delete my saved data” to remove it. The service owner can access server storage.</p><p>{modelStatus}</p><button className="wide" disabled={!token||busy} onClick={erase}><Trash2 size={16}/> Delete my saved data</button><button className="wide secondary" disabled={busy||listening||historyLoading} onClick={disconnect}>Sign out</button></section></div>}
 {login&&<div className="shade"><form className="modal" role="dialog" aria-modal="true" aria-labelledby="login-title" onSubmit={connect}><button type="button" className="close" aria-label="Close" onClick={()=>setLogin(false)}><X/></button><AudioLines className="mint" size={30}/><h2 id="login-title">A space of your own.</h2><p>Continue with your Google account to save your conversations and notes.</p>{!auth&&<p role="status">Google sign-in is not available yet. The owner is finishing setup.</p>}{error&&<p role="alert" className="login-error">{error}</p>}<button className="wide" disabled={loginBusy||!auth}>{loginBusy?'Opening Google…':'Continue with Google'}<ArrowUpRight size={17}/></button></form></div>}
 </div>
}
