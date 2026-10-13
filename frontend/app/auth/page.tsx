import { redirect } from "next/navigation";

export default async function AuthPage({
  searchParams,
}: {
  searchParams?: Promise<{ [key: string]: string | string[] | undefined }>;
}) {
  const resolvedParams = searchParams ? await searchParams : undefined;
  const params = new URLSearchParams();
  if (resolvedParams) {
    for (const [key, value] of Object.entries(resolvedParams)) {
      if (typeof value === "string") {
        params.set(key, value);
      } else if (Array.isArray(value) && value.length > 0) {
        params.set(key, value[0]);
      }
    }
  }

  const qs = params.toString();
  redirect(`/auth/login${qs ? `?${qs}` : ""}`);
}
