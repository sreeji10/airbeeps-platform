import { NextRequest } from "next/server";

const HOP_BY_HOP_HEADERS = new Set([
  "connection",
  "keep-alive",
  "proxy-authenticate",
  "proxy-authorization",
  "te",
  "trailer",
  "transfer-encoding",
  "upgrade",
  "host",
  "content-length",
]);

export const runtime = "nodejs";

type RouteParams = {
  params: Promise<{ path: string[] }>;
};

function resolveBackendBaseUrl(request: NextRequest): string {
  const explicitBase = request.headers.get("x-airbeeps-api-base-url");
  const fallback =
    process.env.AIRBEEPS_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";
  const candidate = explicitBase?.trim() || fallback;

  const parsed = new URL(candidate);
  if (parsed.protocol !== "http:" && parsed.protocol !== "https:") {
    throw new Error("Invalid backend protocol");
  }
  return parsed.toString();
}

function buildTargetUrl(request: NextRequest, baseUrl: string, path: string[]): URL {
  const joined = path.join("/");
  const target = new URL(`/${joined}`, baseUrl);
  request.nextUrl.searchParams.forEach((value, key) => {
    target.searchParams.set(key, value);
  });
  return target;
}

async function proxy(request: NextRequest, params: Promise<{ path: string[] }>) {
  const { path } = await params;

  if (!path.length) {
    return Response.json({ detail: "Missing backend path" }, { status: 400 });
  }

  try {
    const baseUrl = resolveBackendBaseUrl(request);
    const target = buildTargetUrl(request, baseUrl, path);

    const headers = new Headers();
    request.headers.forEach((value, key) => {
      if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase()) && !key.startsWith("x-airbeeps-")) {
        headers.set(key, value);
      }
    });

    if (!headers.has("authorization")) {
      const token = request.cookies.get("airbeeps_auth_token")?.value;
      if (token) {
        headers.set("authorization", `Bearer ${decodeURIComponent(token)}`);
      }
    }

    const upstream = await fetch(target.toString(), {
      method: request.method,
      headers,
      body: request.method === "GET" || request.method === "HEAD" ? undefined : request.body,
      redirect: "manual",
    });

    const responseHeaders = new Headers();
    upstream.headers.forEach((value, key) => {
      if (!HOP_BY_HOP_HEADERS.has(key.toLowerCase())) {
        responseHeaders.set(key, value);
      }
    });

    return new Response(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: responseHeaders,
    });
  } catch (error) {
    const detail = error instanceof Error ? error.message : "Proxy request failed";
    return Response.json({ detail }, { status: 502 });
  }
}

export async function GET(request: NextRequest, context: RouteParams) {
  return proxy(request, context.params);
}

export async function POST(request: NextRequest, context: RouteParams) {
  return proxy(request, context.params);
}

export async function PUT(request: NextRequest, context: RouteParams) {
  return proxy(request, context.params);
}

export async function PATCH(request: NextRequest, context: RouteParams) {
  return proxy(request, context.params);
}

export async function DELETE(request: NextRequest, context: RouteParams) {
  return proxy(request, context.params);
}
