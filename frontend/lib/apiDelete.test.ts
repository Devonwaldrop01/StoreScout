import { afterEach, expect, it, vi } from 'vitest';
vi.mock('@/lib/supabase/client',()=>({createClient:()=>({auth:{getSession:async()=>({data:{session:{access_token:'test'}}})}})}));
import { competitors } from '@/lib/api';
afterEach(()=>vi.unstubAllGlobals());
it('successful competitor deletion does not parse an empty JSON body',async()=>{
  vi.stubGlobal('fetch',vi.fn().mockResolvedValue(new Response(null,{status:204})));
  await expect(competitors.remove('example')).resolves.toBeUndefined();
});
