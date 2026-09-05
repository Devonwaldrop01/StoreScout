import { afterEach, describe, expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
import { GET, POST, PATCH } from '@/app/api/v1/[...path]/route';
afterEach(() => vi.unstubAllGlobals());
describe('API proxy billing and recovery', () => {
  it('forwards signature and exact webhook body bytes', async () => {
    const raw = '{ "message": "é", "spacing": [ 1, 2 ] }';
    const upstream = vi.fn().mockResolvedValue(new Response('{"received":true}'));
    vi.stubGlobal('fetch', upstream);
    await POST(new NextRequest('http://localhost/api/v1/webhooks/stripe-subscriptions', {
      method:'POST',headers:{'stripe-signature':'test-signature'},body:raw,
    }),{params:Promise.resolve({path:['webhooks','stripe-subscriptions']})});
    const options=upstream.mock.calls[0][1];
    expect(options.headers['stripe-signature']).toBe('test-signature');
    expect(new TextDecoder().decode(options.body)).toBe(raw);
  });
  it('returns a useful retryable error when backend is unreachable',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockRejectedValue(new Error('private server details')));
    const res=await GET(new NextRequest('http://localhost/api/v1/competitors'),{params:Promise.resolve({path:['competitors']})});
    expect(res.status).toBe(503);
    expect(await res.text()).not.toContain('private server details');
  });
  it('preserves an upstream retryable webhook failure',async()=>{
    vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response('{"detail":"retry"}',{status:503})));
    const res=await POST(new NextRequest('http://localhost/api/v1/webhooks/stripe-subscriptions',{method:'POST',body:'{}'}),{params:Promise.resolve({path:['webhooks','stripe-subscriptions']})});
    expect(res.status).toBe(503);
  });
});

it('supports editing resources using PATCH', async () => {
  const upstream=vi.fn().mockResolvedValue(new Response('{"data":{}}'));
  vi.stubGlobal('fetch', upstream);
  const res=await PATCH(new NextRequest('http://localhost/api/v1/competitors/c',{method:'PATCH',body:'{"display_name":"Example"}'}),{params:Promise.resolve({path:['competitors','c']})});
  expect(res.status).toBe(200);
  expect(upstream.mock.calls[0][1].method).toBe('PATCH');
});
