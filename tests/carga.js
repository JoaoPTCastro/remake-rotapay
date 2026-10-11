// Sprint D3: carga — registro + busca + dashboard (metas PRD §21).
// Uso: API=http://localhost:8000 TOKEN=$(...) k6 run tests/carga.js
import http from 'k6/http';
import { check } from 'k6';

export const options = {
  vus: 10,
  duration: '30s',
  thresholds: {
    'http_req_duration{rota:busca}': ['p(95)<1000'],
    'http_req_duration{rota:dash}': ['p(95)<2000'],
    'http_req_failed': ['rate<0.01'],
  },
};

const API = __ENV.API || 'http://localhost:8000';
const H = { Authorization: `Bearer ${__ENV.TOKEN}`, 'Content-Type': 'application/json' };

export default function () {
  let r = http.get(`${API}/dashboard`, { headers: H, tags: { rota: 'dash' } });
  check(r, { dash_200: (x) => x.status === 200 });
  r = http.get(`${API}/movimentacoes?q=PIX&limit=50`, { headers: H, tags: { rota: 'busca' } });
  check(r, { busca_200: (x) => x.status === 200 });
  r = http.post(`${API}/movimentacoes`, JSON.stringify({
    data_pix: '2026-09-08', valor: 1.01, remetente: 'k6',
  }), { headers: H, tags: { rota: 'registro' } });
  check(r, { registro_201: (x) => x.status === 201 });
}
