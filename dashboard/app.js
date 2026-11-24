/* Ship4You — dashboard visual. Só desenha: todos os números vêm de dados.js
   gerado por dashboard/gerar_dashboard.py. Nenhum cálculo de modelo aqui. */

const D = window.DADOS;
const COR = {
  real: '#f2604f',
  vogel: '#2ed3a6',
  azul: '#7aa2ff',
  ambar: '#f2b544',
  muted: '#8497b8',
  linha: '#1d2b46',
  painel: '#0e1729',
  texto: '#e9eefb',
};
const RAMPA = ['#12325e', '#1f6f8b', '#2ed3a6', '#f2b544', '#f2604f'];

const fmtInt = (v) => (v == null ? '—' : Math.round(v).toLocaleString('pt-BR'));
const fmtBRL = (v) => (v == null ? '—' : 'R$ ' + Math.round(v).toLocaleString('pt-BR'));
const fmtBRLc = (v) =>
  v == null ? '—'
    : 'R$ ' + v.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtPct = (v, c = 2) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c }) + '%';
const fmtNum = (v, c = 2) =>
  v == null ? '—' : v.toLocaleString('pt-BR', { minimumFractionDigits: c, maximumFractionDigits: c });
const reduzir = (v) => {
  if (v >= 1e6) return fmtNum(v / 1e6, 1) + ' mi';
  if (v >= 1e3) return fmtNum(v / 1e3, 1) + ' mil';
  return fmtInt(v);
};

const graficos = {};      // id -> instância ECharts
const paineis = ['visao', 'rotas', 'mapa', 'sensibilidade', 'validacao'];

const baseEcharts = () => ({
  backgroundColor: 'transparent',
  textStyle: { color: COR.texto, fontFamily: 'inherit' },
  tooltip: {
    backgroundColor: 'rgba(10,17,34,.96)',
    borderColor: '#24344f',
    borderWidth: 1,
    padding: [9, 12],
    textStyle: { color: '#e9eefb', fontSize: 12 },
    extraCssText: 'border-radius:10px; box-shadow:0 10px 26px rgba(0,0,0,.45);',
  },
});

function criar(id, opcao) {
  const el = document.getElementById(id);
  if (!el) return null;
  const ch = echarts.init(el, null, { renderer: 'canvas' });
  ch.setOption(Object.assign(baseEcharts(), opcao));
  graficos[id] = ch;
  return ch;
}

/* ------------------------------------------------------------------ */
/* Cabeçalho, KPIs e rodapé                                            */
/* ------------------------------------------------------------------ */
function preencherCabecalho() {
  const k = D.kpis;
  document.getElementById('kpi-itens').textContent = fmtInt(k.itens);
  document.getElementById('kpi-periodo').textContent =
    'entregues · ' + D.meta.data_min + ' a ' + D.meta.data_max;

  document.getElementById('kpi-real').textContent = fmtBRL(k.custo_real);
  document.getElementById('kpi-real').classList.add('sm');
  document.getElementById('kpi-real-nota').innerHTML =
    'frete efetivamente pago · <b>' + fmtBRLc(k.frete_medio_real) + '</b> por item';

  document.getElementById('kpi-vogel').textContent = fmtBRL(k.custo_vogel);
  document.getElementById('kpi-vogel').classList.add('sm');
  document.getElementById('kpi-vogel-nota').innerHTML =
    'alocação do Vogel · <b>' + fmtBRLc(k.frete_medio_vogel) + '</b> por item';

  document.getElementById('kpi-economia').textContent = fmtPct(k.economia_pct);
  document.getElementById('kpi-economia-nota').innerHTML =
    '<b>' + fmtBRL(k.economia) + '</b> a menos no frete total';

  document.getElementById('kpi-rotas').textContent = fmtInt(k.rotas_ativas);
  document.getElementById('kpi-rotas-nota').textContent =
    'de ' + fmtInt(k.rotas_possiveis) + ' rotas possíveis (' + D.meta.n_origens +
    ' × ' + D.meta.n_destinos + ')';

  document.getElementById('chip-alpha').textContent = fmtNum(D.meta.alpha, 2);
  document.getElementById('chip-cds').textContent = 'CDs · ' + D.meta.cds.join(' ');

  document.getElementById('rodape-fonte').textContent = 'Fonte: ' + D.meta.fonte;
  document.getElementById('rodape-gerado').textContent =
    'Dados gerados por gerar_dashboard.py em ' + D.meta.gerado_em;
}

/* ------------------------------------------------------------------ */
/* Tabela de rotas (ordenável)                                         */
/* ------------------------------------------------------------------ */
const estadoRotas = { ord: 'itens', desc: true };

function renderTabelaRotas() {
  const corpo = document.querySelector('#tabela-rotas tbody');
  const rotas = [...D.rotas];
  const chave = estadoRotas.ord;
  rotas.sort((a, b) => {
    let va, vb;
    if (chave === 'rota') { va = a.o + a.d; vb = b.o + b.d; return estadoRotas.desc ? vb.localeCompare(va) : va.localeCompare(vb); }
    va = a[chave] == null ? -Infinity : a[chave];
    vb = b[chave] == null ? -Infinity : b[chave];
    return estadoRotas.desc ? vb - va : va - vb;
  });

  corpo.innerHTML = rotas.slice(0, 14).map((r) => {
    const economia = r.real != null ? r.real - r.cu : null;
    const classe = economia == null ? 'dim' : economia >= 0 ? 'pos' : 'neg';
    return `<tr>
      <td class="l rota">${r.o}<span class="seta">→</span>${r.d}</td>
      <td>${fmtInt(r.itens)}</td>
      <td>${fmtPct(r.pct, 1)}</td>
      <td>${fmtNum(r.cu, 2)}</td>
      <td class="${classe}">${r.real == null ? '—' : fmtNum(r.real, 2)}</td>
      <td>${fmtBRL(r.ct)}</td>
    </tr>`;
  }).join('');

  document.querySelectorAll('#tabela-rotas th').forEach((th) => {
    th.onclick = () => {
      const campo = th.dataset.ord;
      if (estadoRotas.ord === campo) estadoRotas.desc = !estadoRotas.desc;
      else { estadoRotas.ord = campo; estadoRotas.desc = campo !== 'rota'; }
      renderTabelaRotas();
    };
    th.textContent = th.textContent.replace(/ [▲▼]$/, '');
  });
  const atual = document.querySelector(`#tabela-rotas th[data-ord="${estadoRotas.ord}"]`);
  if (atual) atual.textContent += estadoRotas.desc ? ' ▼' : ' ▲';
}

/* ------------------------------------------------------------------ */
/* Abas, modo apresentação e exportação                                */
/* ------------------------------------------------------------------ */
function trocarPainel(nome, atualizarHash = true) {
  if (atualizarHash && history.replaceState) history.replaceState(null, '', '#' + nome);
  document.querySelectorAll('nav.abas button').forEach((b) => b.classList.remove('ativo'));
  document.querySelectorAll('nav.abas button').forEach((b) =>
    b.classList.toggle('ativo', b.dataset.painel === nome));
  document.querySelectorAll('.painel').forEach((p) =>
    p.classList.toggle('ativo', p.id === 'painel-' + nome));
  Object.values(graficos).forEach((g) => g.resize());
  if (typeof ajustarMapa === 'function') ajustarMapa();
}

function ativarAbas() {
  document.querySelectorAll('nav.abas button').forEach((b) => {
    b.onclick = () => trocarPainel(b.dataset.painel);
  });
  document.addEventListener('keydown', (e) => {
    if (e.target.tagName === 'INPUT') return;
    const atual = paineis.findIndex((p) => document.getElementById('painel-' + p).classList.contains('ativo'));
    if (e.key >= '1' && e.key <= '5') trocarPainel(paineis[Number(e.key) - 1]);
    if (e.key === 'ArrowRight') trocarPainel(paineis[(atual + 1) % paineis.length]);
    if (e.key === 'ArrowLeft') trocarPainel(paineis[(atual - 1 + paineis.length) % paineis.length]);
  });
}

function ativarApresentacao() {
  const btn = document.getElementById('btn-apresentacao');
  btn.onclick = () => {
    const ligado = document.body.classList.toggle('apresentacao');
    btn.textContent = ligado ? 'Sair do modo apresentação' : 'Modo apresentação';
    if (ligado && document.documentElement.requestFullscreen) {
      document.documentElement.requestFullscreen().catch(() => {});
    } else if (!ligado && document.fullscreenElement) {
      document.exitFullscreen().catch(() => {});
    }
    setTimeout(() => Object.values(graficos).forEach((g) => g.resize()), 320);
  };
}

function baixar(chave, nomeArquivo) {
  const ch = graficos[chave];
  if (!ch) return;
  const a = document.createElement('a');
  a.href = ch.getDataURL({ pixelRatio: 2, backgroundColor: '#060b16' });
  a.download = nomeArquivo;
  a.click();
}

function ativarExportacao() {
  document.querySelectorAll('[data-export]').forEach((b) => {
    b.onclick = () => baixar(b.dataset.export, b.dataset.export + '.png');
  });
  document.getElementById('btn-export').onclick = () => {
    const ativo = paineis.find((p) => document.getElementById('painel-' + p).classList.contains('ativo'));
    const ids = Object.keys(graficos).filter((id) => {
      const el = document.getElementById(id);
      return el && el.closest('.painel').id === 'painel-' + ativo;
    });
    ids.forEach((id, i) => setTimeout(() => baixar(id, id + '.png'), i * 260));
  };
}

/* ------------------------------------------------------------------ */
/* 1. Visão geral                                                      */
/* ------------------------------------------------------------------ */
function graficoCascata() {
  const k = D.kpis;
  criar('ch-cascata', {
    grid: { left: 12, right: 16, top: 34, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (ps) => {
        const rotulos = ['Frete real pago', 'Redução pelo Vogel', 'Custo com Vogel'];
        return `<b>${rotulos[ps[0].dataIndex]}</b><br>${fmtBRL(ps[1].value)}`;
      },
    },
    xAxis: {
      type: 'category',
      data: ['Frete real pago', 'Redução pelo Vogel', 'Custo com Vogel'],
      axisLine: { lineStyle: { color: COR.linha } },
      axisTick: { show: false },
      axisLabel: { color: COR.muted, fontSize: 11.5 },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(29,43,70,.55)' } },
      axisLabel: { color: COR.muted, fontSize: 11, formatter: (v) => reduzir(v) },
    },
    series: [
      {
        type: 'bar', stack: 'w', silent: true, itemStyle: { color: 'transparent' },
        data: [0, k.custo_vogel, 0],
      },
      {
        type: 'bar', stack: 'w', barWidth: '46%',
        data: [
          { value: k.custo_real, itemStyle: { color: COR.real, borderRadius: [6, 6, 0, 0] } },
          { value: k.economia, itemStyle: { color: COR.vogel, borderRadius: [6, 6, 0, 0] } },
          { value: k.custo_vogel, itemStyle: { color: '#1f6f8b', borderRadius: [6, 6, 0, 0] } },
        ],
        label: {
          show: true, position: 'top', color: COR.texto, fontSize: 12, fontWeight: 600,
          formatter: (p) => (p.dataIndex === 1 ? '− ' : '') + fmtBRL(p.value),
        },
      },
    ],
  });
}

function graficoRosca() {
  const k = D.kpis;
  criar('ch-rosca', {
    tooltip: { trigger: 'item', formatter: (p) => `${p.name}<br><b>${fmtBRL(p.value)}</b> (${fmtPct(p.percent, 1)})` },
    legend: { bottom: 2, textStyle: { color: COR.muted, fontSize: 11 }, itemWidth: 10, itemHeight: 10 },
    series: [{
      type: 'pie',
      radius: ['56%', '80%'],
      center: ['50%', '48%'],
      avoidLabelOverlap: true,
      itemStyle: { borderColor: COR.painel, borderWidth: 3 },
      label: {
        show: true, position: 'center', formatter: () => `{a|${fmtPct(k.economia_pct, 2)}}\n{b|de economia}`,
        rich: {
          a: { fontSize: 28, fontWeight: 700, color: COR.vogel, lineHeight: 34 },
          b: { fontSize: 12, color: COR.muted },
        },
      },
      emphasis: { label: { show: true } },
      data: [
        { name: 'Custo mantido (Vogel)', value: k.custo_vogel, itemStyle: { color: '#1f6f8b' } },
        { name: 'Economia gerada', value: k.economia, itemStyle: { color: COR.vogel } },
      ],
    }],
  });
}

function graficoUF() {
  const linhas = Object.entries(D.ufs)
    .map(([uf, d]) => ({ uf, nome: d.nome, eco: d.origem ? d.origem.economia : 0 }))
    .sort((a, b) => b.eco - a.eco)
    .slice(0, 12)
    .reverse();

  criar('ch-uf', {
    grid: { left: 8, right: 62, top: 12, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis', axisPointer: { type: 'shadow' },
      formatter: (ps) => {
        const p = ps[0];
        return `<b>${p.name}</b><br>Economia: ${fmtBRL(p.value)}`;
      },
    },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: 'rgba(29,43,70,.55)' } },
      axisLabel: { color: COR.muted, fontSize: 11, formatter: (v) => reduzir(v) },
    },
    yAxis: {
      type: 'category',
      data: linhas.map((l) => l.uf),
      axisLine: { lineStyle: { color: COR.linha } },
      axisTick: { show: false },
      axisLabel: { color: COR.texto, fontSize: 11.5, fontWeight: 600 },
    },
    series: [{
      type: 'bar',
      barWidth: '62%',
      data: linhas.map((l) => ({
        value: l.eco,
        itemStyle: {
          color: l.eco >= 0 ? COR.vogel : COR.real,
          borderRadius: [0, 4, 4, 0],
        },
      })),
      label: {
        show: true, position: 'right', color: COR.muted, fontSize: 10.5,
        formatter: (p) => fmtBRL(p.value),
      },
    }],
  });
}

function graficoMes() {
  const meses = D.meses;
  criar('ch-mes', {
    grid: { left: 8, right: 12, top: 30, bottom: 8, containLabel: true },
    tooltip: {
      trigger: 'axis',
      formatter: (ps) => {
        const i = ps[0].dataIndex;
        return `<b>${meses[i].ym}</b><br>Itens: ${fmtInt(meses[i].itens)}` +
          `<br>Frete médio: ${fmtBRLc(meses[i].frete / meses[i].itens)}`;
      },
    },
    xAxis: {
      type: 'category',
      data: meses.map((m) => m.ym.slice(2)),
      axisLine: { lineStyle: { color: COR.linha } },
      axisTick: { show: false },
      axisLabel: { color: COR.muted, fontSize: 10, interval: 1 },
    },
    yAxis: [
      {
        type: 'value',
        splitLine: { lineStyle: { color: 'rgba(29,43,70,.55)' } },
        axisLabel: { color: COR.muted, fontSize: 10.5, formatter: (v) => reduzir(v) },
      },
      {
        type: 'value',
        splitLine: { show: false },
        axisLabel: { color: COR.ambar, fontSize: 10.5, formatter: (v) => 'R$ ' + fmtNum(v, 0) },
      },
    ],
    series: [
      {
        type: 'bar', name: 'Itens', barWidth: '58%',
        itemStyle: { color: 'rgba(122,162,255,.55)', borderRadius: [3, 3, 0, 0] },
        data: meses.map((m) => m.itens),
      },
      {
        type: 'line', name: 'Frete médio', yAxisIndex: 1, smooth: true, symbol: 'circle',
        symbolSize: 5, lineStyle: { width: 2.2, color: COR.ambar },
        itemStyle: { color: COR.ambar },
        areaStyle: { color: 'rgba(242,181,68,.08)' },
        data: meses.map((m) => +(m.frete / m.itens).toFixed(2)),
      },
    ],
  });
}

/* ------------------------------------------------------------------ */
/* 2. Rotas                                                            */
/* ------------------------------------------------------------------ */
function graficoMatriz() {
  const m = D.matriz;
  const dados = [];
  for (let i = 0; i < m.origens.length; i++) {
    for (let j = 0; j < m.destinos.length; j++) {
      const itens = m.aloc[i][j];
      const custo = m.custo[i][j];
      dados.push({
        value: [j, i, itens > 0 ? Math.log10(itens) : -1],
        itens, custo,
        total: itens * custo,
      });
    }
  }
  const maxLog = Math.max(...dados.map((d) => (d.itens > 0 ? d.value[2] : 0)));
  const rota = {};
  D.rotas.forEach((r) => { rota[r.o + '>' + r.d] = r; });

  criar('ch-matriz', {
    grid: { left: 8, right: 14, top: 12, bottom: 44, containLabel: true },
    tooltip: {
      formatter: (p) => {
        const o = m.origens[p.data.value[1]];
        const d = m.destinos[p.data.value[0]];
        if (!p.data.itens) return `<b>${o} → ${d}</b><br><span style="color:${COR.muted}">sem alocação</span>`;
        const r = rota[o + '>' + d];
        const real = r && r.real != null ? `<br>Frete real: ${fmtNum(r.real, 2)} /item` : '';
        return `<b>${o} → ${d}</b><br>Itens: ${fmtInt(p.data.itens)}` +
          `<br>Custo Vogel: ${fmtNum(p.data.custo, 2)} /item` +
          `<br>Custo total: ${fmtBRL(p.data.total)}` + real;
      },
    },
    xAxis: {
      type: 'category', data: m.destinos, splitArea: { show: false },
      axisLine: { lineStyle: { color: COR.linha } },
      axisTick: { show: false },
      axisLabel: { color: COR.muted, fontSize: 10.5, interval: 0, rotate: 0 },
    },
    yAxis: {
      type: 'category', data: m.origens, inverse: true,
      axisLine: { lineStyle: { color: COR.linha } },
      axisTick: { show: false },
      axisLabel: { color: COR.muted, fontSize: 10.5, fontWeight: 600 },
    },
    visualMap: {
      min: 0, max: maxLog, calculable: true, orient: 'horizontal',
      left: 'center', bottom: 2, itemWidth: 14, itemHeight: 150,
      textStyle: { color: COR.muted, fontSize: 10.5 },
      inRange: { color: RAMPA },
      formatter: (v) => fmtInt(Math.round(Math.pow(10, v))),
    },
    series: [{
      type: 'heatmap',
      data: dados,
      itemStyle: { borderColor: '#0b1425', borderWidth: 1.5 },
      emphasis: { itemStyle: { borderColor: '#fff', borderWidth: 1 } },
    }],
  });
}

function graficoDispersao() {
  const comReal = D.rotas.filter((r) => r.real != null);
  const maxCt = Math.max(...comReal.map((r) => r.ct));
  criar('ch-disp', {
    grid: { left: 8, right: 18, top: 40, bottom: 8, containLabel: true },
    tooltip: {
      formatter: (p) => {
        const r = p.data.rota;
        const eco = r.real - r.cu;
        return `<b>${r.o} → ${r.d}</b><br>Itens: ${fmtInt(r.itens)} (${fmtPct(r.pct, 1)} do volume)` +
          `<br>Custo Vogel: ${fmtNum(r.cu, 2)} /item<br>Frete real: ${fmtNum(r.real, 2)} /item` +
          `<br>Diferença: ${eco >= 0 ? '−' : '+'}${fmtNum(Math.abs(eco), 2)} /item` +
          `<br>Custo total: ${fmtBRL(r.ct)}`;
      },
    },
    xAxis: {
      type: 'value', name: 'Itens alocados', nameTextStyle: { color: COR.muted, fontSize: 10.5 },
      splitLine: { lineStyle: { color: 'rgba(29,43,70,.55)' } },
      axisLabel: { color: COR.muted, fontSize: 10, formatter: (v) => reduzir(v) },
    },
    yAxis: {
      type: 'value', name: 'R$ / item', nameGap: 16, nameTextStyle: { color: COR.muted, fontSize: 10.5 },
      splitLine: { lineStyle: { color: 'rgba(29,43,70,.55)' } },
      axisLabel: { color: COR.muted, fontSize: 10 },
    },
    series: [{
      type: 'scatter',
      data: comReal.map((r) => ({
        rota: r,
        value: [r.itens, r.cu],
        symbolSize: 8 + 30 * Math.sqrt(r.ct / maxCt),
        itemStyle: {
          color: r.real - r.cu >= 0 ? 'rgba(46,211,166,.72)' : 'rgba(242,96,79,.72)',
          borderColor: r.real - r.cu >= 0 ? COR.vogel : COR.real,
          borderWidth: 1,
        },
      })),
    }],
  });
}

/* ------------------------------------------------------------------ */
/* 3. Mapa do Brasil (projeção Albers já pronta nos dados)              */
/* ------------------------------------------------------------------ */
const mapa = {
  metrica: 'itens',
  uf: null,
  instancia: null,
  cellPx: 6,
};

const METRICAS = {
  itens: { rotulo: 'Itens', valor: (c) => c.i, fmt: (v) => fmtInt(v) },
  pedidos: { rotulo: 'Pedidos', valor: (c) => c.p, fmt: (v) => fmtInt(v) },
  frete: {
    rotulo: 'Frete médio (R$/item)',
    valor: (c) => c.f / c.i,
    fmt: (v) => 'R$ ' + fmtNum(v, 2),
  },
};

function dadosCelulas() {
  const m = METRICAS[mapa.metrica];
  return D.mapa.grade.map((c) => {
    const v = m.valor(c);
    return { value: [c.x, c.y, mapa.log ? Math.log10(Math.max(v, 1)) : v], cel: c };
  });
}

function opcaoMapa(xMin, xMax, yMin, yMax) {
  const m = METRICAS[mapa.metrica];
  // corta os extremos por percentil: sem isso quase toda célula fica azul-escura
  // (o volume se concentra em poucas células) e o mapa perde a leitura de calor
  const valores = dadosCelulas().map((d) => d.value[2]).sort((a, b) => a - b);
  const quantil = (q) => valores[Math.min(valores.length - 1, Math.max(0, Math.floor(q * valores.length)))];
  const minV = quantil(0.05);
  const maxV = quantil(0.98);
  const reais = D.mapa.grade.map((c) => m.valor(c));
  const realMin = Math.min(...reais);
  const realMax = Math.max(...reais);
  const ufs = Object.entries(D.ufs).filter(([, d]) => d.xy);

  const arcos = D.mapa.arcos
    .filter((a) => !mapa.uf || a.o === mapa.uf || a.d === mapa.uf)
    .map((a) => ({
      coords: a.pts,
      arco: a,
      lineStyle: {
        width: 1.3 + 6 * Math.sqrt(a.pct / 42),
        opacity: mapa.uf ? 0.95 : 0.68,
        color: mapa.uf && a.o === mapa.uf ? COR.ambar : COR.azul,
      },
    }));

  return {
    grid: { left: 0, right: 0, top: 0, bottom: 0 },
    tooltip: {
      formatter: (p) => {
        if (p.seriesName === 'calor') {
          const c = p.data.cel;
          return `Célula · ${fmtInt(c.p)} pedidos` +
            `<br>Itens: <b>${fmtInt(c.i)}</b>` +
            `<br>Frete médio: ${fmtBRLc(c.f / c.i)}`;
        }
        if (p.seriesName === 'rotas') {
          const a = p.data.arco;
          return `<b>${a.o} → ${a.d}</b><br>Itens: ${fmtInt(a.itens)} (${fmtPct(a.pct, 1)} do volume)`;
        }
        if (p.seriesName === 'ufs') {
          const uf = p.data.uf;
          const d = D.ufs[uf];
          return `<b>${uf} · ${d.nome}</b><br>Itens que saem: ${d.origem ? fmtInt(d.origem.itens) : '0'}` +
            `<br>Itens que entram: ${d.destino ? fmtInt(d.destino.itens) : '0'}` +
            `<br><span style="color:${COR.muted}">clique para detalhar</span>`;
        }
        return '';
      },
    },
    xAxis: { type: 'value', min: xMin, max: xMax, show: false },
    yAxis: { type: 'value', min: yMin, max: yMax, inverse: true, show: false },
    visualMap: {
      show: true, min: minV, max: maxV, calculable: false, orient: 'horizontal',
      left: 14, bottom: 4, itemWidth: 11, itemHeight: 130, precision: 0,
      text: [`${m.rotulo}: ${m.fmt(realMax)}`, m.fmt(realMin)],
      textStyle: { color: COR.muted, fontSize: 10 },
      inRange: { color: RAMPA },
      formatter: (v) => (mapa.log ? fmtInt(Math.round(Math.pow(10, v))) : m.fmt(v)),
    },
    series: [
      {
        name: 'calor', type: 'scatter', symbol: 'circle',
        symbolSize: mapa.cellPx * 2.3,
        data: dadosCelulas(),
        itemStyle: { opacity: 0.8 },
        emphasis: { scale: 1.5, itemStyle: { opacity: 1 } },
        z: 1,
      },
      {
        name: 'contornos', type: 'lines', polyline: true, coordinateSystem: 'cartesian2d',
        silent: true, z: 2,
        lineStyle: { color: 'rgba(122,162,255,.30)', width: 1.1 },
        data: D.mapa.contornos.map((c) => ({ coords: c.pts })),
      },
      {
        name: 'rotas', type: 'lines', polyline: true, coordinateSystem: 'cartesian2d', z: 3,
        data: arcos,
        lineStyle: { color: COR.azul },
        emphasis: { lineStyle: { width: 4, opacity: 1 } },
      },
      {
        name: 'ufs', type: 'scatter', z: 4,
        data: ufs.map(([uf, d]) => ({
          value: [d.xy[0], d.xy[1], d.destino ? d.destino.itens : 0],
          uf,
          symbolSize: mapa.uf === uf ? 0 : 8 + 14 * Math.sqrt((d.destino ? d.destino.itens : 0) / 60000),
          itemStyle: {
            color: d.cd ? 'rgba(242,181,68,.16)' : 'rgba(122,162,255,.08)',
            borderColor: d.cd ? COR.ambar : 'rgba(122,162,255,.45)',
            borderWidth: d.cd ? 1.6 : 1,
          },
          label: {
            show: true, formatter: uf, position: 'inside',
            color: d.cd ? COR.ambar : '#eaf1ff', fontSize: 10.5, fontWeight: 700,
            textBorderColor: 'rgba(4,9,18,.9)', textBorderWidth: 3,
          },
        })),
        emphasis: { itemStyle: { borderColor: '#fff' } },
      },
    ],
  };
}

function ajustarMapa() {
  const ch = mapa.instancia;
  if (!ch) return;
  const rect = ch.getDom().getBoundingClientRect();
  if (!rect.width || !rect.height) return;

  const ext = D.mapa.extensao;
  const larguraGeo = ext.x1 - ext.x0;
  const alturaGeo = ext.y1 - ext.y0;

  // mesma escala em x e y (o Brasil não pode esticar), com o desenho centralizado
  const escala = Math.min(rect.width / larguraGeo, rect.height / alturaGeo);
  mapa.cellPx = escala * D.mapa.escala_grau * D.mapa.passo_grau;
  mapa.log = mapa.metrica === 'itens' || mapa.metrica === 'pedidos';

  const visivelX = rect.width / escala;
  const visivelY = rect.height / escala;
  const xMin = ext.x0 - (visivelX - larguraGeo) / 2;
  const yMin = ext.y0 - (visivelY - alturaGeo) / 2;

  ch.setOption(opcaoMapa(xMin, xMin + visivelX, yMin, yMin + visivelY));
}

function graficoMapa() {
  const cont = document.getElementById('metricas-mapa');
  cont.innerHTML = Object.entries(METRICAS)
    .map(([k, m]) => `<button data-metrica="${k}" class="${k === mapa.metrica ? 'ativo' : ''}">${m.rotulo}</button>`)
    .join('');
  cont.querySelectorAll('button').forEach((b) => {
    b.onclick = () => {
      mapa.metrica = b.dataset.metrica;
      cont.querySelectorAll('button').forEach((x) => x.classList.toggle('ativo', x === b));
      ajustarMapa();
    };
  });

  mapa.instancia = criar('ch-mapa', {});
  mapa.instancia.on('click', (p) => {
    if (p.seriesName === 'ufs') {
      mapa.uf = mapa.uf === p.data.uf ? null : p.data.uf;
      detalharUF(mapa.uf);
      ajustarMapa();
    }
  });
  ajustarMapa();
  detalharUF(null);
}

function detalharUF(uf) {
  const titulo = document.getElementById('uf-titulo');
  const desc = document.getElementById('uf-desc');
  const info = document.getElementById('uf-info');

  if (!uf) {
    titulo.textContent = 'Estado';
    desc.textContent = 'Clique numa sigla do mapa';
    const top = D.rotas.slice(0, 3);
    info.innerHTML = '<div class="vazio">Selecione um estado para ver oferta, demanda, frete real e custo do Vogel daquele estado.' +
      '<br><br>As três rotas de maior volume hoje:<br>' +
      top.map((r) => `<b>${r.o} → ${r.d}</b> · ${fmtPct(r.pct, 1)} do volume`).join('<br>') + '</div>';
    return;
  }

  const d = D.ufs[uf];
  titulo.textContent = uf + ' · ' + d.nome;
  desc.textContent = d.cd ? 'Centro de distribuição candidato' : 'Estado da rede';
  const linhas = [];
  if (d.origem) {
    linhas.push(['Itens que saem', fmtInt(d.origem.itens)]);
    linhas.push(['Frete real (saída)', fmtBRL(d.origem.frete_real)]);
    linhas.push(['Frete médio real', fmtNum(d.origem.frete_medio, 2)]);
    linhas.push(['Custo Vogel', fmtBRL(d.origem.custo_vogel)]);
    linhas.push(['Frete médio Vogel', fmtNum(d.origem.frete_medio_vogel, 2)]);
    linhas.push(['<b>Economia na origem</b>', `<b class="pos">${fmtBRL(d.origem.economia)}</b>`]);
  }
  if (d.destino) {
    linhas.push(['Itens que entram', fmtInt(d.destino.itens)]);
    linhas.push(['Frete médio recebido', fmtNum(d.destino.frete_medio, 2)]);
    linhas.push(['Frete médio Vogel', fmtNum(d.destino.frete_medio_vogel, 2)]);
  }
  const rotasUf = D.rotas.filter((r) => r.o === uf).slice(0, 4);
  info.innerHTML = linhas.map(([a, b]) => `<div class="linha"><span>${a}</span><span>${b}</span></div>`).join('') +
    (rotasUf.length
      ? '<div class="vazio" style="margin-top:10px">Principais saídas: ' +
        rotasUf.map((r) => `<b>${r.o} → ${r.d}</b> ${fmtPct(r.pct, 1)}`).join(' · ') + '</div>'
      : '');
}

/* ------------------------------------------------------------------ */
/* 4. Sensibilidade                                                    */
/* ------------------------------------------------------------------ */
function graficoSensibilidade() {
  const s = D.sensibilidade;
  const todos = s.map((r) => r.custo_vogel).concat([D.kpis.custo_real]);
  const margem = 0.22 * (Math.max(...todos) - Math.min(...todos));
  criar('ch-sens', {
    grid: { left: 8, right: 22, top: 26, bottom: 8, containLabel: true },
    tooltip: {
      formatter: (p) => {
        const r = s[p.dataIndex];
        return `<b>α = ${fmtNum(r.alpha, 2)}</b><br>Custo Vogel: ${fmtBRL(r.custo_vogel)}` +
          `<br>Economia: ${fmtBRL(r.economia_reais)} (${fmtPct(r.economia_pct, 2)})`;
      },
    },
    xAxis: {
      type: 'value', min: 0.2, max: 1.06,
      name: 'α', nameTextStyle: { color: COR.muted },
      splitLine: { lineStyle: { color: 'rgba(29,43,70,.55)' } },
      axisLabel: { color: COR.muted, fontSize: 11, formatter: (v) => fmtNum(v, 1) },
    },
    yAxis: {
      type: 'value',
      min: Math.floor((Math.min(...todos) - margem) / 1000) * 1000,
      max: Math.ceil((Math.max(...todos) + margem) / 1000) * 1000,
      splitLine: { lineStyle: { color: 'rgba(29,43,70,.55)' } },
      axisLabel: { color: COR.muted, fontSize: 11, formatter: (v) => reduzir(v) },
    },
    series: [{
      type: 'line',
      data: s.map((r) => [r.alpha, r.custo_vogel]),
      smooth: 0.35,
      symbol: 'circle',
      symbolSize: (v, p) => (s[p.dataIndex].atual ? 14 : 8),
      lineStyle: { width: 2.6, color: COR.vogel },
      itemStyle: { color: COR.vogel, borderColor: '#0b1425', borderWidth: 2 },
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(46,211,166,.24)' },
          { offset: 1, color: 'rgba(46,211,166,0)' },
        ]),
      },
      markLine: {
        silent: true, symbol: 'none',
        lineStyle: { color: COR.real, type: 'dashed', width: 1.4 },
        label: {
          formatter: 'frete real pago (sem otimização)', color: COR.real, fontSize: 10.5,
          position: 'insideStartTop',
        },
        data: [{ yAxis: D.kpis.custo_real }],
      },
      label: {
        show: true, position: 'bottom', distance: 10, color: COR.muted, fontSize: 10,
        formatter: (p) => fmtPct(s[p.dataIndex].economia_pct, 1),
      },
    }],
  });
}

/* ------------------------------------------------------------------ */
/* 5. Validação                                                        */
/* ------------------------------------------------------------------ */
function renderChecks() {
  const cont = document.getElementById('lista-checks');
  cont.innerHTML = D.checks.map((c) => `<div class="check">
      <div class="marca ${c.ok ? '' : 'falha'}">${c.ok ? '✓' : '!'}</div>
      <div class="txt">${c.restricao}<small>${c.detalhe}</small></div>
    </div>`).join('');
  const todos = D.checks.every((c) => c.ok);
  document.getElementById('selo').innerHTML = todos
    ? '<div class="selo">✓ Solução factível — todas as restrições do modelo foram respeitadas</div>'
    : '<div class="selo" style="background:rgba(242,96,79,.1);border-color:rgba(242,96,79,.35);color:#f2604f">' +
      '! Solução com restrição violada</div>';
}

function renderDiagnostico() {
  const m = D.meta;
  const linhas = [
    ['Itens entregues', fmtInt(D.kpis.itens)],
    ['Período da base', m.data_min + ' a ' + m.data_max],
    ['Matriz de custo', m.n_origens + ' origens × ' + m.n_destinos + ' destinos'],
    ['Rotas possíveis', fmtInt(m.rotas_possiveis)],
    ['Rotas com histórico no recorte', fmtInt(m.rotas_com_historico)],
    ['Estimadas pela base completa', fmtInt(m.rotas_estimadas)],
    ['Centros de distribuição', m.cds.join(' · ')],
    ['α (desconto de consolidação)', fmtNum(m.alpha, 2)],
    ['Frete médio real', fmtBRLc(D.kpis.frete_medio_real)],
    ['Frete médio Vogel', fmtBRLc(D.kpis.frete_medio_vogel)],
  ];
  document.getElementById('diagnostico').innerHTML =
    linhas.map(([a, b]) => `<div class="linha"><span>${a}</span><span>${b}</span></div>`).join('');
}

function renderSensibilidadeTabela() {
  const corpo = document.querySelector('#tabela-sens tbody');
  corpo.innerHTML = D.sensibilidade.map((r) => `<tr${r.atual ? ' style="background:rgba(46,211,166,.08)"' : ''}>
      <td class="l">${fmtNum(r.alpha, 2)}${r.atual ? ' <span class="pos">· usado</span>' : ''}</td>
      <td>${fmtBRL(r.custo_vogel)}</td>
      <td class="pos">${fmtBRL(r.economia_reais)}</td>
      <td>${fmtPct(r.economia_pct, 2)}</td>
    </tr>`).join('');

  document.getElementById('sens-leitura').innerHTML =
    'Mesmo com <b>α = 1,00</b> (CD sem desconto) a economia fica em <b>' +
    fmtPct(D.sensibilidade[D.sensibilidade.length - 1].economia_pct, 1) +
    '</b>: o ganho principal vem de mandar cada volume pela rota de menor frete médio, não do desconto hipotético. ' +
    'A curva não é monotônica porque o Vogel é heurístico (alocação gulosa): o número do relatório é a faixa, não um ponto.';
}

/* ------------------------------------------------------------------ */
/* Inicialização                                                       */
/* ------------------------------------------------------------------ */
function iniciar() {
  // abre direto na aba do hash (#rotas, #mapa, #mapa-SP, ...) para facilitar a gravação
  const hash = location.hash.replace('#', '').split('-');
  if (paineis.includes(hash[0])) trocarPainel(hash[0], false);
  const ufInicial = hash[1] && D.ufs[hash[1]] ? hash[1] : null;

  preencherCabecalho();
  ativarAbas();
  ativarApresentacao();
  ativarExportacao();

  graficoCascata();
  graficoRosca();
  graficoUF();
  graficoMes();
  graficoMatriz();
  graficoDispersao();
  graficoMapa();
  graficoSensibilidade();

  renderTabelaRotas();
  renderChecks();
  renderDiagnostico();
  renderSensibilidadeTabela();

  if (ufInicial) {
    mapa.uf = ufInicial;
    detalharUF(ufInicial);
  }

  Object.values(graficos).forEach((g) => g.resize());
  ajustarMapa();

  let t = null;
  window.addEventListener('resize', () => {
    clearTimeout(t);
    t = setTimeout(() => {
      Object.values(graficos).forEach((g) => g.resize());
      ajustarMapa();
    }, 120);
  });
}

document.addEventListener('DOMContentLoaded', iniciar);
