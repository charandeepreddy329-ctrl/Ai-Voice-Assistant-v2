// @vitest-environment jsdom
import React from 'react';
import { afterEach, beforeEach, expect, test, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';
const mock = vi.hoisted(()=>({session:null, callback:null, signIn:vi.fn(), signOut:vi.fn()}));
vi.mock('../src/auth',()=>({auth:{auth:{
 getSession:async()=>({data:{session:mock.session}}),
 onAuthStateChange:cb=>{mock.callback=cb;return {data:{subscription:{unsubscribe(){}}}}},
 signInWithOAuth:(...args)=>mock.signIn(...args),
 signOut:(...args)=>mock.signOut(...args),
}}}));
vi.mock('../src/Orb',()=>({default:()=> <div>3D assistant</div>}));
import App from '../src/App';
const session = (id,token='fresh-token')=>({access_token:token,user:{id,email:id+'@example.com'}});
let requests;
beforeEach(()=>{
 mock.session=null;mock.signIn.mockReset().mockResolvedValue({error:null});mock.signOut.mockReset();
 Element.prototype.scrollIntoView=vi.fn();window.matchMedia=()=>({matches:true});
 requests=[];
 vi.stubGlobal('fetch',vi.fn(async(url,opts={})=>{
  requests.push({url,opts});
  const data=url.endsWith('/api/history')?{messages:[{role:'assistant',text:'Saved private history'}]}:
   url.endsWith('/api/model-status')?{message:'Settings present, not yet connected'}:
   url.endsWith('/api/chat')?{text:'The answer is 84.'}:{status:'ok'};
  return {ok:true,json:async()=>data};
 }));
});
afterEach(()=>{cleanup();vi.unstubAllGlobals()});

test('Google sign-in requests the provider with an exact same-origin return URL',async()=>{
 render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Sign in'}));
 fireEvent.click(screen.getByRole('button',{name:'Continue with Google'}));
 await waitFor(()=>expect(mock.signIn).toHaveBeenCalledWith({provider:'google',options:{redirectTo:window.location.origin+'/'}}));
 expect(screen.queryByLabelText('Email address')).toBeNull();
 expect(screen.queryByLabelText('Workspace access code')).toBeNull();
});

test('Google provider errors remain visible and allow retry',async()=>{
 mock.signIn.mockResolvedValue({error:{message:'Google sign-in is not enabled.'}});
 render(<App/>);fireEvent.click(screen.getByRole('button',{name:'Sign in'}));
 fireEvent.click(screen.getByRole('button',{name:'Continue with Google'}));
 await waitFor(()=>expect(screen.getAllByRole('alert').some(x=>x.textContent.includes('not enabled'))).toBe(true));
 expect(screen.getByRole('button',{name:'Continue with Google'}).disabled).toBe(false);
});

test('restores history, refreshes request token, and clears private content on signout',async()=>{
 mock.session=session('account-a');
 render(<App/>);await screen.findByText('Saved private history');
 mock.session=session('account-a','refreshed-token');
 fireEvent.change(screen.getByLabelText('Message Nova'),{target:{value:'calculate 12 * 7'}});
 fireEvent.click(screen.getByRole('button',{name:'Send message'}));
 await screen.findByText('The answer is 84.');
 expect(requests.find(r=>r.url.endsWith('/api/chat')).opts.headers.Authorization).toBe('Bearer refreshed-token');
 act(()=>{mock.session=null;mock.callback('SIGNED_OUT',null)});
 expect(screen.queryByText('Saved private history')).toBeNull();
 expect(screen.queryByText('The answer is 84.')).toBeNull();
});

test('a late chat response cannot appear after changing accounts',async()=>{
 mock.session=session('account-a');
 const normalFetch=fetch;let resolveChat;
 vi.stubGlobal('fetch',vi.fn((url,opts)=>url.endsWith('/api/chat')?new Promise(resolve=>{resolveChat=resolve}):normalFetch(url,opts)));
 render(<App/>);await screen.findByText('Saved private history');
 fireEvent.change(screen.getByLabelText('Message Nova'),{target:{value:'private question'}});
 fireEvent.click(screen.getByRole('button',{name:'Send message'}));
 await waitFor(()=>expect(resolveChat).toBeTypeOf('function'));
 await act(async()=>{mock.session=session('account-b');mock.callback('SIGNED_IN',mock.session)});
 await act(async()=>resolveChat({ok:true,json:async()=>({text:'Secret answer for account A'})}));
 expect(screen.queryByText('Secret answer for account A')).toBeNull();
 expect(screen.queryByText('private question')).toBeNull();
});
