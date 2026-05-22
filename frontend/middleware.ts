import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";

export async function middleware(request: NextRequest) {
  // Skip auth check if env vars not configured (build time / undeployed)
  const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;
  if (!supabaseUrl || !supabaseKey) {
    return NextResponse.next({ request });
  }

  let supabaseResponse = NextResponse.next({ request });

  const supabase = createServerClient(
    supabaseUrl,
    supabaseKey,
    {
      cookies: {
        getAll() {
          return request.cookies.getAll();
        },
        setAll(cookiesToSet) {
          cookiesToSet.forEach(({ name, value }) => request.cookies.set(name, value));
          supabaseResponse = NextResponse.next({ request });
          cookiesToSet.forEach(({ name, value, options }) =>
            supabaseResponse.cookies.set(name, value, options)
          );
        },
      },
    }
  );

  const { data: { user } } = await supabase.auth.getUser();
  const { pathname } = request.nextUrl;

  // Protect /dashboard, /alerts, /settings
  const isAppRoute = pathname.startsWith("/dashboard") ||
    pathname.startsWith("/alerts") ||
    pathname.startsWith("/settings");

  if (isAppRoute && !user) {
    return NextResponse.redirect(new URL("/auth/login", request.url));
  }

  // Redirect logged-in users away from auth pages
  if (user && (pathname.startsWith("/auth/login") || pathname.startsWith("/auth/signup"))) {
    return NextResponse.redirect(new URL("/dashboard", request.url));
  }

  return supabaseResponse;
}

export const config = {
  matcher: ["/dashboard/:path*", "/alerts/:path*", "/settings/:path*", "/auth/:path*"],
};
