import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.API_URL || "http://localhost:10000";

async function proxy(request: NextRequest, path: string[]) {
  const { search } = new URL(request.url);
  const target = `${BACKEND}/api/v1/${path.join("/")}${search}`;

  const headers: Record<string, string> = {
    "content-type": "application/json",
  };
  const auth = request.headers.get("authorization");
  if (auth) headers["authorization"] = auth;
  // Admin console (/admin/store-index) authenticates with this header
  const adminToken = request.headers.get("x-admin-token");
  if (adminToken) headers["x-admin-token"] = adminToken;
  const signature = request.headers.get("stripe-signature");
  if (signature) headers["stripe-signature"] = signature;

  const body =
    request.method !== "GET" && request.method !== "HEAD"
      ? await request.arrayBuffer()
      : undefined;

  let res: Response;
  try {
    res = await fetch(target, {
      method: request.method, headers, body, cache: "no-store",
      signal: AbortSignal.timeout(120_000),
    });
  } catch {
    return NextResponse.json(
      { detail: "StoreScout is temporarily unavailable. Please try again." },
      { status: 503 },
    );
  }
  const text = await res.text();
  return new NextResponse(res.status === 204 || res.status === 304 ? null : text, {
    status: res.status,
    headers: { "content-type": res.headers.get("content-type") || "application/json" },
  });
}

export async function GET(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}

export async function POST(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}

export async function PUT(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}

export async function PATCH(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}

export async function DELETE(
  req: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  return proxy(req, (await params).path);
}
