import { expect, it, vi } from 'vitest';
import { NextRequest } from 'next/server';
vi.mock('@/lib/supabase/server',()=>({createClient:async()=>({auth:{exchangeCodeForSession:async()=>({error:null})}})}));
import { GET } from '@/app/auth/callback/route';
it.each(['@evil.example','https://evil.example','//evil.example','/\\evil.example'])('rejects unsafe auth return URL %s',async(next)=>{
  const res=await GET(new NextRequest(`https://getstorescout.com/auth/callback?code=test&next=${encodeURIComponent(next)}`));
  expect(res.headers.get('location')).toBe('https://getstorescout.com/onboarding');
});
it('preserves a valid local reset-password destination',async()=>{
  const res=await GET(new NextRequest('https://getstorescout.com/auth/callback?code=test&next=/auth/reset-password'));
  expect(res.headers.get('location')).toBe('https://getstorescout.com/auth/reset-password');
});
