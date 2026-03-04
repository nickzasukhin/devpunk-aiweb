import React, { useEffect, useState } from 'react'
import { getConfig, updateConfig } from '../api/admin'
import { changePassword } from '../api/auth'
import { useAuth } from '../context/AuthContext'

const ANTHROPIC_MODELS = ['claude-sonnet-4-6','claude-haiku-4-5','claude-opus-4-6']
const OPENAI_MODELS = ['gpt-4o','gpt-4o-mini','gpt-4-turbo']
const EMBEDDING_MODELS = ['text-embedding-3-small','text-embedding-3-large','voyage-3']
const ELEVENLABS_MODELS = ['eleven_multilingual_v2','eleven_turbo_v2_5']
const VAPI_VOICES = [
  {id:'Elliot',label:'Elliot (Male, EN)'},
  {id:'Jennifer',label:'Jennifer (Female, EN)'},
  {id:'Rohan',label:'Rohan (Male, EN-IN)'},
  {id:'Lily',label:'Lily (Female, EN-GB)'},
  {id:'Paola',label:'Paola (Female, EN)'},
  {id:'Cole',label:'Cole (Male, EN)'},
  {id:'Ryan',label:'Ryan (Male, EN)'},
  {id:'Bria',label:'Bria (Female, EN)'},
  {id:'Aria',label:'Aria (Female, EN)'},
  {id:'Roger',label:'Roger (Male, EN)'},
  {id:'Sarah',label:'Sarah (Female, EN)'},
]

export default function AgentConfig() {
  const { user } = useAuth()
  const [cfg, setCfg] = useState<Record<string,string>>({})
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState('')
  const [pwForm, setPwForm] = useState({current:'',next:'',msg:''})

  useEffect(() => { getConfig().then(r=>{setCfg(r.data);setLoading(false)}) }, [])

  const set = (key: string, val: string) => setCfg(p => ({...p, [key]: val}))

  const save = async () => {
    setSaving(true); setMsg('')
    try { await updateConfig(cfg); setMsg('Saved ✓') } catch { setMsg('Error saving') }
    setSaving(false)
    setTimeout(()=>setMsg(''),2000)
  }

  const changePw = async (e: React.FormEvent) => {
    e.preventDefault()
    try {
      await changePassword(pwForm.current, pwForm.next)
      setPwForm({current:'',next:'',msg:'Password changed ✓'})
    } catch { setPwForm(p=>({...p,msg:'Wrong current password'})) }
  }

  const Slider = ({k,label,min=0,max=1,step=0.05}:{k:string,label:string,min?:number,max?:number,step?:number}) => (
    <label style={{display:'block',marginBottom:14}}>
      <div style={{display:'flex',justifyContent:'space-between',fontSize:12,color:'var(--text-muted)',marginBottom:5}}>
        <span>{label}</span><span>{parseFloat(cfg[k]||'0').toFixed(2)}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={cfg[k]||'0'} onChange={e=>set(k,e.target.value)}
        style={{padding:0,border:'none',background:'transparent',accentColor:'var(--accent)'}} />
    </label>
  )

  if (loading) return <div style={{color:'var(--text-muted)'}}>Loading...</div>

  return (
    <div>
      <div style={{display:'flex',justifyContent:'space-between',alignItems:'center',marginBottom:20}}>
        <h1 style={{fontSize:20,fontWeight:600}}>Agent Config</h1>
        <div style={{display:'flex',gap:8,alignItems:'center'}}>
          {msg && <span style={{fontSize:12,color:'var(--success)'}}>{msg}</span>}
          <button className="btn-primary" onClick={save} disabled={saving}>{saving?'Saving...':'Save changes'}</button>
        </div>
      </div>

      <div style={{display:'grid',gridTemplateColumns:'1fr 1fr',gap:20}}>
        {/* Sales Agent */}
        <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,padding:20}}>
          <h3 style={{fontWeight:600,marginBottom:16,fontSize:14}}>🤖 Sales Agent (Text)</h3>
          <label style={{display:'block',marginBottom:14}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>System Prompt</div>
            <textarea rows={6} value={cfg.sales_system_prompt||''} onChange={e=>set('sales_system_prompt',e.target.value)} style={{resize:'vertical'}} />
          </label>
          <div style={{marginBottom:14}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:6}}>LLM Provider</div>
            <div style={{display:'flex',gap:12}}>
              {['anthropic','openai'].map(p=>(
                <label key={p} style={{display:'flex',alignItems:'center',gap:6,cursor:'pointer',fontSize:13}}>
                  <input type="radio" name="llm_provider" value={p} checked={cfg.llm_provider===p||(!cfg.llm_provider&&p==='anthropic')} onChange={()=>set('llm_provider',p)} style={{width:'auto',accentColor:'var(--accent)'}} />
                  {p.charAt(0).toUpperCase()+p.slice(1)}
                </label>
              ))}
            </div>
          </div>
          <label style={{display:'block',marginBottom:14}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>Model</div>
            <select value={cfg.llm_model||''} onChange={e=>set('llm_model',e.target.value)}>
              <optgroup label="Anthropic">{ANTHROPIC_MODELS.map(m=><option key={m}>{m}</option>)}</optgroup>
              <optgroup label="OpenAI">{OPENAI_MODELS.map(m=><option key={m}>{m}</option>)}</optgroup>
            </select>
          </label>
          <Slider k="llm_temperature" label="Temperature" />
        </div>

        {/* Voice Agent */}
        <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,padding:20}}>
          <h3 style={{fontWeight:600,marginBottom:16,fontSize:14}}>🎙 Voice Agent</h3>
          <label style={{display:'block',marginBottom:14}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>System Prompt</div>
            <textarea rows={4} value={cfg.voice_system_prompt||''} onChange={e=>set('voice_system_prompt',e.target.value)} style={{resize:'vertical'}} />
          </label>
          <label style={{display:'block',marginBottom:14}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>First Message (greeting)</div>
            <input value={cfg.voice_first_message||''} onChange={e=>set('voice_first_message',e.target.value)} placeholder="Hi! I'm the DevPunks AI assistant..." />
          </label>
          <div style={{marginBottom:14}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:6}}>Voice Provider</div>
            <div style={{display:'flex',gap:12}}>
              {['vapi','elevenlabs'].map(p=>(
                <label key={p} style={{display:'flex',alignItems:'center',gap:6,cursor:'pointer',fontSize:13}}>
                  <input type="radio" name="voice_provider" value={p} checked={(cfg.voice_provider||'vapi')===p} onChange={()=>set('voice_provider',p)} style={{width:'auto',accentColor:'var(--accent)'}} />
                  {p==='vapi'?'Vapi (built-in)':'ElevenLabs Conversational AI'}
                </label>
              ))}
            </div>
          </div>

          {(cfg.voice_provider||'vapi')==='vapi' ? (<>
            <label style={{display:'block',marginBottom:14}}>
              <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>Voice</div>
              <select value={cfg.vapi_voice_id||'Elliot'} onChange={e=>set('vapi_voice_id',e.target.value)}>
                {VAPI_VOICES.map(v=><option key={v.id} value={v.id}>{v.label}</option>)}
              </select>
            </label>
            <Slider k="vapi_voice_speed" label="Speed" min={0.25} max={2} step={0.05} />
          </>) : (<>
            <label style={{display:'block',marginBottom:14}}>
              <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>Voice ID</div>
              <input value={cfg.elevenlabs_voice_id||''} onChange={e=>set('elevenlabs_voice_id',e.target.value)} placeholder="ElevenLabs Voice ID" />
            </label>
            <label style={{display:'block',marginBottom:14}}>
              <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>Model</div>
              <select value={cfg.elevenlabs_model||'eleven_multilingual_v2'} onChange={e=>set('elevenlabs_model',e.target.value)}>
                {ELEVENLABS_MODELS.map(m=><option key={m}>{m}</option>)}
              </select>
            </label>
            <Slider k="elevenlabs_stability" label="Stability" />
            <Slider k="elevenlabs_similarity_boost" label="Similarity Boost" />
            <Slider k="elevenlabs_style" label="Style / Emotion" />
          </>)}
        </div>

        {/* Embeddings */}
        <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,padding:20}}>
          <h3 style={{fontWeight:600,marginBottom:16,fontSize:14}}>🔍 Embeddings</h3>
          <div style={{marginBottom:14}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:6}}>Provider</div>
            <div style={{display:'flex',gap:12}}>
              {['openai','voyage'].map(p=>(
                <label key={p} style={{display:'flex',alignItems:'center',gap:6,cursor:'pointer',fontSize:13}}>
                  <input type="radio" name="embedding_provider" value={p} checked={cfg.embedding_provider===p||(!cfg.embedding_provider&&p==='openai')} onChange={()=>set('embedding_provider',p)} style={{width:'auto',accentColor:'var(--accent)'}} />
                  {p.charAt(0).toUpperCase()+p.slice(1)}
                </label>
              ))}
            </div>
          </div>
          <label style={{display:'block'}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:5}}>Model</div>
            <select value={cfg.embedding_model||'text-embedding-3-small'} onChange={e=>set('embedding_model',e.target.value)}>
              {EMBEDDING_MODELS.map(m=><option key={m}>{m}</option>)}
            </select>
          </label>
        </div>

        {/* API Keys */}
        <div style={{background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,padding:20}}>
          <h3 style={{fontWeight:600,marginBottom:16,fontSize:14}}>🔑 API Keys</h3>
          {[
            {k:'anthropic_api_key',label:'Anthropic API Key',ph:'sk-ant-...'},
            {k:'openai_api_key',label:'OpenAI API Key',ph:'sk-...'},
            {k:'elevenlabs_api_key',label:'ElevenLabs API Key',ph:'...'},
            {k:'vapi_api_key',label:'Vapi API Key',ph:'...'},
          ].map(({k,label,ph})=>(
            <label key={k} style={{display:'block',marginBottom:12}}>
              <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:4}}>{label}</div>
              <input type="password" value={cfg[k]||''} onChange={e=>set(k,e.target.value)} placeholder={ph} autoComplete="off" />
            </label>
          ))}
        </div>
      </div>

      {/* Change Password */}
      <div style={{marginTop:20,background:'var(--bg-card)',border:'1px solid var(--border)',borderRadius:8,padding:20,maxWidth:400}}>
        <h3 style={{fontWeight:600,marginBottom:14,fontSize:14}}>🔒 Change Password</h3>
        <form onSubmit={changePw}>
          <label style={{display:'block',marginBottom:10}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:4}}>Current password</div>
            <input type="password" value={pwForm.current} onChange={e=>setPwForm(p=>({...p,current:e.target.value}))} required />
          </label>
          <label style={{display:'block',marginBottom:14}}>
            <div style={{fontSize:12,color:'var(--text-muted)',marginBottom:4}}>New password</div>
            <input type="password" value={pwForm.next} onChange={e=>setPwForm(p=>({...p,next:e.target.value}))} required />
          </label>
          {pwForm.msg && <div style={{fontSize:12,color:pwForm.msg.includes('✓')?'var(--success)':'var(--danger)',marginBottom:8}}>{pwForm.msg}</div>}
          <button type="submit" className="btn-secondary">Update password</button>
        </form>
      </div>
    </div>
  )
}
