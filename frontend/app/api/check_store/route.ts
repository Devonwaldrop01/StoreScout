import { NextRequest, NextResponse } from "next/server";

const BACKEND = process.env.API_URL || "http://localhost:10000";

export async function GET(request: NextRequest) {
  const storeUrl = new URL(request.url).searchParams.get("store_url") || "";
  const res = await fetch(
    `${BACKEND}/check_store?store_url=${encodeURIComponent(storeUrl)}`
  );
  const data = await res.json();
  return NextResponse.json(data, { status: res.status });
}
