/* ============================================================
   Pages B — RQ3 Simulator, AI Assistant, Safe Recommendation
   ============================================================ */
const { useState: useStateB, useMemo: useMemoB, useRef: useRefB, useEffect: useEffectB } = React;
const {
  KpiCard, Callout, Chip, StabilityBadge, SliderControl, Select, NumberInput, RadioGroup,
  ChartCard, PageHead, Section, Table, ChatBubble, PromptChip, HBarChart,
  CHANNELS, CH_SHORT, CH_EFF, METHODS, METHOD_WEIGHTS, METHOD_STABILITY,
  LABEL_SCENARIOS, fmtMoney, fmtInt, normalize, Icon,
} = window;
const eB = React.createElement;

/* ---------------------------------------------------------------
   PAGE 4 — RQ3 Interactive Simulator
   --------------------------------------------------------------- */
function RQ3Page() {
  const [budget, setBudget] = useStateB(100000);
  const [rev, setRev] = useStateB(100);
  const [scenarioId, setScenarioId] = useStateB('as-labeled');
  const [method, setMethod] = useStateB('Markov');
  const [mode, setMode] = useStateB('auto');
  const [manual, setManual] = useStateB([20,10,25,15,20,10]);

  const scenario = LABEL_SCENARIOS.find(s=>s.id===scenarioId);
  const mult = scenario.mult;
  const B = (typeof budget==='number'&&budget>0)?budget:0;
  const R = (typeof rev==='number'&&rev>0)?rev:0;

  const weights = useMemoB(()=>{
    const raw = mode==='auto' ? METHOD_WEIGHTS[method] : manual;
    return normalize(raw);
  },[mode,method,manual]);

  const conv = i => (B*weights[i]/1000)*CH_EFF[i]*mult;
  const rows = CHANNELS.map((c,i)=>({ ch:c, w:weights[i], alloc:B*weights[i], conv:conv(i) }));
  const totalConv = rows.reduce((a,r)=>a+r.conv,0);
  const totalRev = totalConv*R;

  // equal-split baseline
  const eqW = normalize([1,1,1,1,1,1]);
  const eqConv = CHANNELS.reduce((a,c,i)=>a+(B*eqW[i]/1000)*CH_EFF[i]*mult,0);
  const eqRev = eqConv*R;
  const dConv = totalConv-eqConv, dRev = totalRev-eqRev;

  // stability
  let stabScore;
  if (mode==='auto') stabScore = METHOD_STABILITY[method];
  else { const spread = Math.max(...weights)-Math.min(...weights); stabScore = Math.max(-0.2, 1-spread*4.2); }
  const stabState = stabScore>=0.7?'stable':stabScore>=0.3?'moderate':'unstable';

  const dClass = v => v>0.5?'delta-up':v<-0.5?'delta-down':'delta-flat';
  const dSign = v => (v>0?'+':'')+v.toLocaleString('en-US',{maximumFractionDigits:0});

  return eB('div',{className:'page'},
    eB(PageHead,{
      eyebrow:'RQ3 · INTERACTIVE SIMULATOR',
      title:'Given the limitations, what analysis strategy is safer?',
      desc:'A what-if diagnostic. Move the inputs to see how fragile any “allocation” becomes across attribution methods and label scenarios.'}),

    eB('div',{className:'split',style:{marginTop:18}},
      /* ---- INPUT PANEL ---- */
      eB('div',{className:'card card-pad',style:{display:'flex',flexDirection:'column',gap:15}},
        eB('div',{className:'eyebrow-mono'},'INPUTS'),
        eB(NumberInput,{label:'Total marketing budget', value:budget, prefix:'$', step:1000, min:0, onChange:setBudget}),
        eB(NumberInput,{label:'Revenue per conversion', value:rev, prefix:'$', step:5, min:0, onChange:setRev}),
        eB(Select,{label:'Conversion label scenario', value:scenarioId,
          onChange:setScenarioId, hint:scenario.note,
          options:LABEL_SCENARIOS.map(s=>({value:s.id,label:s.name}))}),
        eB(Select,{label:'Attribution method', value:method, onChange:setMethod,
          options:METHODS}),
        eB('div',{className:'field'},
          eB('label',{className:'field-label'},'Allocation mode'),
          eB(RadioGroup,{value:mode, onChange:setMode, options:[
            {value:'auto', label:'Auto from method', sub:'Weights derived from '+method},
            {value:'manual', label:'Manual channel sliders', sub:'Set each channel share by hand'},
          ]})),
        mode==='manual' ? eB('div',{style:{display:'flex',flexDirection:'column',gap:11,paddingTop:2}},
          eB('div',{className:'field-hint',style:{display:'flex',justifyContent:'space-between'}},
            eB('span',null,'Channel shares'), eB('span',{className:'mono'},'Normalized to 100%')),
          CHANNELS.map((c,i)=>eB('div',{key:i,style:{display:'flex',alignItems:'center',gap:10}},
            eB('span',{style:{width:88,fontSize:11.5,color:'var(--ink-2)'}}, c),
            eB('input',{type:'range',className:'rng',style:{flex:1},min:0,max:40,step:1,value:manual[i],
              onChange:ev=>{ const m=[...manual]; m[i]=parseFloat(ev.target.value); setManual(m); }}),
            eB('span',{className:'mono num',style:{width:42,textAlign:'right',fontSize:11.5,color:'var(--navy)'}},
              (weights[i]*100).toFixed(0)+'%')))) : null
      ),

      /* ---- OUTPUT PANEL ---- */
      eB('div',{style:{display:'flex',flexDirection:'column',gap:14}},
        eB('div',{className:'card'},
          eB('div',{style:{padding:'11px 15px',borderBottom:'1px solid var(--line)',display:'flex',justifyContent:'space-between',alignItems:'center'}},
            eB('span',{className:'section-title'},'Budget allocation'),
            eB(StabilityBadge,{state:stabState})),
          eB('table',{className:'tbl'},
            eB('thead',null,eB('tr',null,
              eB('th',null,'Channel'), eB('th',{className:'r'},'Weight'),
              eB('th',{className:'r'},'Allocation'), eB('th',{className:'r'},'Est. conv.'))),
            eB('tbody',null,
              rows.map((r,i)=>eB('tr',{key:i},
                eB('td',null,r.ch),
                eB('td',{className:'r num'},(r.w*100).toFixed(1)+'%'),
                eB('td',{className:'r'},fmtMoney(r.alloc)),
                eB('td',{className:'r'},r.conv.toFixed(1)))),
              eB('tr',{className:'row-total'},
                eB('td',null,'Total'),
                eB('td',{className:'r num'},'100.0%'),
                eB('td',{className:'r'},fmtMoney(B)),
                eB('td',{className:'r'},totalConv.toFixed(1)))))),

        eB('div',{className:'grid-2'},
          eB('div',{className:'bignum-card accent'},
            eB('div',{className:'bn-label'},'Estimated conversions'),
            eB('div',{className:'bn-value num'}, totalConv.toLocaleString('en-US',{maximumFractionDigits:0})),
            eB('div',{className:'bn-sub'},'scenario ×'+mult.toFixed(2))),
          eB('div',{className:'bignum-card'},
            eB('div',{className:'bn-label'},'Estimated revenue'),
            eB('div',{className:'bn-value num'}, fmtMoney(totalRev)),
            eB('div',{className:'bn-sub'},'@ '+fmtMoney(R)+' / conv'))),

        eB('div',{className:'grid-2'},
          eB('div',{className:'delta-card'},
            eB('div',{className:'d-label'},'Δ conversions vs. equal split'),
            eB('div',{className:'d-value '+dClass(dConv)+' num'}, dSign(dConv))),
          eB('div',{className:'delta-card'},
            eB('div',{className:'d-label'},'Δ revenue vs. equal split'),
            eB('div',{className:'d-value '+dClass(dRev)+' num'}, (dRev>0?'+':'')+fmtMoney(dRev).replace('$', dRev<0?'-$':'$').replace('-$-','-$')))),

        eB(Callout,{title:'What-if diagnostic — not a recommendation'},
          'This simulator uses precomputed evidence from a validity-questionable dataset. It is a what-if diagnostic tool, ',
          eB('b',null,'not a causal budget recommendation'),'. A ',eB('b',null,stabState),
          ' stability reading means the ranking ',stabState==='stable'?'is comparatively robust here, but still rests on suspect labels':'re-orders under plausible label corrections.')
      )
    )
  );
}

/* ---------------------------------------------------------------
   PAGE 5 — AI Research Assistant
   --------------------------------------------------------------- */
const PROMPTS = [
  'Tóm tắt kết luận 3 RQ',
  'Vì sao conversion rate 83.63% là vấn đề?',
  'Có nên dùng dataset này để chọn channel thắng không?',
  'Giải thích sensitivity analysis',
];

function answerFor(text) {
  const t = text.toLowerCase();
  if (t.includes('tóm tắt') || t.includes('3 rq') || t.includes('summar'))
    return eB('div',null,
      eB('p',null,'Summary across the three research questions:'),
      eB('ul',null,
        eB('li',null,eB('b',null,'RQ1 — '),'The dataset is ',eB('span',{className:'b-warn'},'not valid'),' for direct attribution. User any-Yes is ',eB('span',{className:'b-num'},'83.63%'),', ~28× a 3% benchmark.'),
        eB('li',null,eB('b',null,'RQ2 — '),'Channel signal is statistically inert (AUC ',eB('span',{className:'b-num'},'0.4902'),', χ² p ',eB('span',{className:'b-num'},'0.8598'),'). Journey length, not channel, drives the label.'),
        eB('li',null,eB('b',null,'RQ3 — '),'Allocations re-order across label scenarios; stability is low. Use sensitivity ranges, not a single “winner”.')));
  if (t.includes('83.63') || t.includes('conversion rate') || t.includes('vấn đề'))
    return eB('div',null,
      eB('p',null,'A ',eB('span',{className:'b-num'},'83.63%'),' user any-Yes rate is implausible for e-commerce, where user-level conversion typically sits near ',eB('span',{className:'b-num'},'2–4%'),'.'),
      eB('p',null,'It signals ',eB('span',{className:'b-warn'},'label saturation'),': the Yes label fires mid-journey, repeats per user (1,731 users with multiple Yes), and is not aligned to a final outcome. Any model trained on it learns the labelling process, not real conversion.'));
  if (t.includes('channel') && (t.includes('thắng') || t.includes('winner') || t.includes('chọn')))
    return eB('div',null,
      eB('p',null,eB('span',{className:'b-warn'},'No.'),' You should not pick a winning channel from this dataset.'),
      eB('p',null,'Channel identity does not predict conversion (AUC ',eB('span',{className:'b-num'},'0.4902'),", Cramér's V ",eB('span',{className:'b-num'},'0.0139'),'). Apparent differences are confounded by journey length. Declaring a winner would be a causal claim the evidence cannot support.'));
  if (t.includes('sensitivity'))
    return eB('div',null,
      eB('p',null,'Sensitivity analysis re-runs the allocation under six conversion-label scenarios (as-labeled → conservative) and several attribution methods.'),
      eB('p',null,'Because per-channel shares ',eB('span',{className:'b-warn'},'re-order'),' across these scenarios — e.g. Email falls from ~20.5% to ~7% — the result is not robust. Report the ',eB('b',null,'range'),' of outcomes and the stability badge, never a single point estimate.'));
  if (t.includes('trình bày') || t.includes('thầy') || t.includes('present'))
    return eB('div',null,
      eB('p',null,'A defensible framing for your committee:'),
      eB('ul',null,
        eB('li',null,'Lead with the ',eB('span',{className:'b-num'},'83.63%'),' label-saturation finding as the headline validity issue.'),
        eB('li',null,'Show the channel-vs-length AUC comparison to establish confounding.'),
        eB('li',null,'Present sensitivity ranges, and state plainly the data supports ',eB('b',null,'audit, not attribution'),'.'),
        eB('li',null,'Close with the “Safer strategies” checklist as your recommendation.')));
  return eB('div',null,
    eB('p',null,'I answer only from this project’s precomputed evidence. The core finding: the dataset has a ',eB('span',{className:'b-warn'},'conversion-label validity problem'),' (83.63% saturation, channel AUC 0.4902) and should be used for a validity audit rather than direct attribution.'),
    eB('p',null,'Try one of the example prompts above for a grounded summary.'));
}

function AssistantPage() {
  const [msgs, setMsgs] = useStateB([
    { role:'assistant', node: eB('div',null,
      eB('p',null,'Hello — I’m the project research assistant. I answer strictly from this study’s precomputed evidence about the MTA dataset’s validity.'),
      eB('p',null,'Ask about the three research questions, the 83.63% label issue, or how to present the findings.')) }
  ]);
  const [draft, setDraft] = useStateB('');
  const [thinking, setThinking] = useStateB(false);
  const scrollRef = useRefB(null);

  useEffectB(()=>{ const el=scrollRef.current; if(el) el.scrollTop = el.scrollHeight; },[msgs,thinking]);

  function send(text) {
    const q = (text!=null?text:draft).trim();
    if (!q || thinking) return;
    setMsgs(m=>[...m,{role:'user',node:eB('p',null,q)}]);
    setDraft('');
    setThinking(true);
    setTimeout(()=>{
      setMsgs(m=>[...m,{role:'assistant',node:answerFor(q)}]);
      setThinking(false);
    }, 650);
  }

  return eB('div',{className:'page',style:{height:'100%',display:'flex',flexDirection:'column',paddingBottom:18}},
    eB(PageHead,{
      eyebrow:'AI RESEARCH ASSISTANT',
      title:'Ask the evidence',
      desc:'A grounded assistant for interrogating the validity findings. It does not browse the web or invent numbers.'}),

    eB('div',{className:'chat-notice'},
      eB('span',{className:'gem'}, Icon.info({s:15})),
      eB('span',null,'Powered by Gemini. Answers grounded in project evidence only. May make mistakes.')),

    eB('div',{className:'chat-wrap',style:{flex:1,minHeight:0}},
      eB('div',{className:'chat-scroll',ref:scrollRef},
        msgs.map((m,i)=>eB(ChatBubble,{key:i,role:m.role}, m.node)),
        thinking ? eB(ChatBubble,{role:'assistant'},
          eB('span',{style:{color:'var(--ink-3)',fontStyle:'italic'}},'Retrieving from evidence…')) : null),

      eB('div',{style:{paddingTop:14}},
        eB('div',{className:'prompt-chips'},
          PROMPTS.map((p,i)=>eB(PromptChip,{key:i,onClick:()=>send(p)}, p))),
        eB('div',{className:'chat-input-bar'},
          eB('textarea',{rows:1,placeholder:'Ask about the dataset’s validity…',value:draft,
            onChange:ev=>setDraft(ev.target.value),
            onKeyDown:ev=>{ if(ev.key==='Enter'&&!ev.shiftKey){ ev.preventDefault(); send(); } }}),
          eB('button',{className:'send-btn',disabled:!draft.trim()||thinking,onClick:()=>send()}, Icon.send({s:16})))))
  );
}

/* ---------------------------------------------------------------
   PAGE 6 — Safe Recommendation
   --------------------------------------------------------------- */
function SafePage() {
  const steps = [
    { idx:'STEP 1', title:'Ingest & profile', desc:'Load touchpoints, profile label distribution' },
    { idx:'STEP 2', title:'Validity audit', desc:'Test label saturation & channel signal' },
    { idx:'STEP 3', title:'Confounding check', desc:'Separate journey-length from channel' },
    { idx:'STEP 4', title:'Sensitivity ranges', desc:'Re-run across label scenarios' },
    { idx:'OUTPUT', title:'Audit report', desc:'Disclose limits — no channel winner', terminal:true },
  ];
  const dos = [
    'Use the dataset for validity audit, not direct attribution',
    'Treat conversion labels as suspect until validated',
    'Report sensitivity ranges, not point estimates',
    'Disclose the 83.63% label saturation prominently',
  ];
  const donts = [
    'Do not claim a causal channel winner',
    'Do not optimize budget directly from this dataset',
    'Do not use the row-level label for individual attribution',
  ];

  return eB('div',{className:'page'},
    eB(PageHead,{
      eyebrow:'SAFE RECOMMENDATION',
      title:'Given the limitations, the safer path forward',
      desc:'A defensible workflow and a do / do-not list that keep conclusions inside what the evidence supports.'}),

    eB(Section,{title:'Recommended analysis workflow'},
      eB('div',{className:'flow'},
        steps.map((s,i)=>[
          eB('div',{key:'s'+i,className:'flow-step'+(s.terminal?' terminal':'')},
            eB('div',{className:'fs-idx'}, s.idx),
            eB('div',{className:'fs-title'}, s.title),
            eB('div',{className:'fs-desc'}, s.desc)),
          i<steps.length-1 ? eB('div',{key:'a'+i,className:'flow-arrow'}, Icon.arrowR({s:18})) : null
        ]))),

    eB('div',{className:'grid-2',style:{marginTop:22,alignItems:'start'}},
      eB('div',{className:'card card-pad'},
        eB('div',{style:{display:'flex',alignItems:'center',gap:8,marginBottom:13}},
          eB('span',{style:{color:'var(--ok)'}}, Icon.check({s:18})),
          eB('span',{className:'section-title'},'Safer analysis strategies')),
        eB('ul',{className:'list-check list-do'},
          dos.map((d,i)=>eB('li',{key:i},
            eB('span',{className:'ico'}, Icon.check({s:16})), d)))),

      eB('div',{className:'card card-pad',style:{background:'var(--amber-tint)',borderColor:'var(--amber-line)'}},
        eB('div',{style:{display:'flex',alignItems:'center',gap:8,marginBottom:13}},
          eB('span',{style:{color:'var(--amber)'}}, Icon.warn({s:18})),
          eB('span',{className:'section-title',style:{color:'var(--amber-700)'}},'Do NOT')),
        eB('ul',{className:'list-check list-dont'},
          donts.map((d,i)=>eB('li',{key:i},
            eB('span',{className:'ico',style:{color:'var(--amber)'}}, Icon.x({s:16})), d))))),

    eB('div',{style:{marginTop:20}},
      eB(Callout,{neutral:true, title:'Bottom line'},
        'This dataset is valuable as a ',eB('b',null,'validity-audit artefact'),' and a teaching example of label bias — not as a source of causal channel credit. Frame every downstream claim as conditional on resolving the conversion-label problem first.'))
  );
}

Object.assign(window, { RQ3Page, AssistantPage, SafePage });
