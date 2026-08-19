<script setup>
import { computed, nextTick, onMounted, ref } from 'vue'

const apiBase = import.meta.env.VITE_API_BASE || '/api/v1'
const sessionId = `web-${crypto.randomUUID()}`
const userId = 'demo-user'
const messages = ref([{ role: 'assistant', text: '你好，我是 SmartCare。可以咨询会员规则，也可以查询订单、物流或申请退款。' }])
const input = ref('')
const loading = ref(false)
const pending = ref(null)
const examples = ref([])
const scroller = ref(null)
const status = computed(() => loading.value ? '正在思考' : '在线')

onMounted(async () => {
  try { const r = await fetch(`${apiBase}/demo`); examples.value = (await r.json()).examples } catch { examples.value = ['会员积分多久过期？','查询订单 ORD-20260801'] }
})

async function scrollBottom(){ await nextTick(); if(scroller.value) scroller.value.scrollTop = scroller.value.scrollHeight }
async function send(text=input.value){
  if(!text.trim() || loading.value) return
  messages.value.push({role:'user',text}); input.value=''; loading.value=true; await scrollBottom()
  try{
    const r=await fetch(`${apiBase}/chat`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text,session_id:sessionId,user_id:userId})})
    if(!r.ok) throw new Error('服务暂不可用')
    const data=await r.json(); messages.value.push({role:'assistant',text:data.answer,meta:{intent:data.intent,route:data.route,sources:data.sources,tools:data.tool_trace}})
    pending.value=data.confirmation_token ? {token:data.confirmation_token} : null
  }catch(e){ messages.value.push({role:'assistant',text:`请求失败：${e.message}`}) }
  finally{ loading.value=false; await scrollBottom() }
}
async function confirm(confirmed){
  if(!pending.value) return
  loading.value=true
  try{
    const r=await fetch(`${apiBase}/refund/confirm`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({confirmation_token:pending.value.token,session_id:sessionId,user_id:userId,confirmed})})
    const data=await r.json(); messages.value.push({role:'assistant',text:data.answer,meta:{tools:data.tool_trace}}); pending.value=null
  }finally{loading.value=false; await scrollBottom()}
}
</script>

<template>
  <main class="shell">
    <aside>
      <div class="brand"><span class="logo">S</span><div><strong>SmartCare</strong><small>AI Customer Service</small></div></div>
      <div class="status"><i></i>{{ status }}</div>
      <section><label>体验账号</label><b>demo-user</b><span>数据隔离已开启</span></section>
      <section><label>可用能力</label><ul><li>知识库问答</li><li>订单与物流查询</li><li>退款二次确认</li><li>多轮会话记忆</li></ul></section>
      <p class="safe">高风险操作由服务端校验，不由模型直接执行。</p>
    </aside>
    <section class="chat">
      <header><div><h1>智能客服 Agent</h1><p>RAG · Tool Calling · Memory</p></div><span class="badge">DEMO</span></header>
      <div class="messages" ref="scroller">
        <article v-for="(m,i) in messages" :key="i" :class="m.role">
          <div class="bubble">{{ m.text }}</div>
          <div v-if="m.meta" class="meta">
            <span v-if="m.meta.intent">{{ m.meta.intent }} / {{ m.meta.route }}</span>
            <details v-if="m.meta.sources?.length"><summary>查看引用来源</summary><p v-for="s in m.meta.sources" :key="s.title"><b>{{s.title}}</b> · {{s.score}}<br/>{{s.snippet}}</p></details>
            <details v-if="m.meta.tools?.length"><summary>查看工具轨迹</summary><pre>{{JSON.stringify(m.meta.tools,null,2)}}</pre></details>
          </div>
        </article>
        <article v-if="loading" class="assistant"><div class="bubble typing"><i></i><i></i><i></i></div></article>
      </div>
      <div v-if="pending" class="confirm"><div><b>需要你的确认</b><span>退款属于资金相关操作，确认后才会执行。</span></div><button class="ghost" @click="confirm(false)">取消</button><button @click="confirm(true)">确认退款</button></div>
      <div class="examples"><button v-for="x in examples" :key="x" @click="send(x)">{{x}}</button></div>
      <form @submit.prevent="send()"><textarea v-model="input" @keydown.enter.exact.prevent="send()" placeholder="输入问题，Enter 发送…"></textarea><button :disabled="loading">发送</button></form>
      <footer>AI 生成内容可能有误，重要操作将要求二次确认。</footer>
    </section>
  </main>
</template>

