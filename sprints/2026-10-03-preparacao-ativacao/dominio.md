# Domínio rotapay.site — diagnóstico e proposta

03/10/2026. Domínio informado pelo usuário; nenhuma alteração DNS/proxy autorizada ou realizada.

## Verificado

DNS A de rotapay.site: 2.57.91.91. www resolve por alias para rotapay.site, mesmo IPv4. Nenhum AAAA retornado. Nameservers horizon.dns-parking.com e orbit.dns-parking.com. A VPS por SSH confirma IPv4 público2.24.108.54. HTTP do domínio200 via servidor hcdn; HTTPS falhou com alerta TLS internal error. Isto não confirma serviço RotaPay no domínio. Caddy atual da VPS tem somente bloco :80 encaminhando para127.0.0.1:3000; nenhum domínio configurado.

## Proposta concreta — aplicar somente após autorização

No painel DNS do domínio, substituir registro A do nome @ por2.24.108.54; manter www como CNAME para rotapay.site, verificando se não há registros conflitantes. Não alterar MX/TXT e outros registros de email. Confirmar DNS antes de emitir certificado.

Na VPS preservar cópia privada do Caddyfile atual, validar o candidato dominio.Caddyfile e substituir/recarregar apenas após autorização. O candidato encaminha para o painel operacional atual na porta3000, nunca para o ambiente sintético3128. Caddy obtém HTTPS automaticamente se DNS/portas80/443 estiverem disponíveis. Não transformar a homologação sintética em publicação real por engano.

Conferir certificado e login, rotas protegidas e proxy/API após alteração; não aceitar apenas200 na raiz. Em falha, recuperar Caddyfile anterior e recarregar; avaliar o DNS separadamente porque propagação não é instantânea.

## Distinção de entregas

Conectar domínio à versão operacional atual é ação externa separada da promoção do candidato Sprint18. A preparação técnica da versão nova não autoriza sua ativação. Escolher explicitamente se o domínio será conectado à versão atual ou somente durante a janela da nova versão.
