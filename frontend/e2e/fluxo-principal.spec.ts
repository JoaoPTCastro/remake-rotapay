import { test, expect } from '@playwright/test';

// Fluxo principal: login → dashboard → registrar PIX (redireciona ao detalhe)
// → conferir no Controle (busca/filtro/exportação).
test('fluxo principal do painel', async ({ page }) => {
  await page.goto('/login');
  await page.getByLabel('Email').fill('admin@local');
  await page.getByLabel('Senha').fill('admin123');
  await page.getByRole('button', { name: 'Entrar' }).click();
  await expect(page.getByText('Como está minha situação financeira agora?').first()).toBeVisible();

  await page.goto('/movimentacoes');
  const centavos = String(Math.floor(Math.random() * 90) + 10);
  await page.locator('input[name="data_pix"]').fill('2026-09-08');
  await page.locator('input[name="valor"]').fill(`7.${centavos}`);
  await page.locator('input[name="remetente"]').fill('E2E Playwright');
  await page.getByRole('button', { name: 'Registrar', exact: true }).click();
  await expect(page.getByText(/PIX-\d{6} — R\$ 7\./)).toBeVisible();

  await page.goto('/controle');
  await page.getByPlaceholder('Buscar código, remetente…').fill('E2E Playwright');
  await page.getByRole('button', { name: 'Filtrar' }).click();
  await expect(page.getByText(`7.${centavos}`).first()).toBeVisible();

  const download = page.waitForEvent('download');
  await page.getByRole('link', { name: /Exportar CSV/ }).click();
  expect((await download).suggestedFilename()).toContain('.csv');
});