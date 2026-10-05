import { useLayoutEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

export function useSanitizedTokens<const T extends readonly string[]>(names: T) {
  const location = useLocation();
  const navigate = useNavigate();
  const [tokens] = useState<Record<T[number], string>>(() => {
    const search = new URLSearchParams(location.search);
    return Object.fromEntries(names.map((name) => [name, search.get(name) ?? ""])) as Record<T[number], string>;
  });

  useLayoutEffect(() => {
    const search = new URLSearchParams(location.search);
    let changed = false;
    for (const name of names) {
      if (search.has(name)) {
        search.delete(name);
        changed = true;
      }
    }
    if (changed) {
      void navigate({ pathname: location.pathname, search: search.toString() }, { replace: true });
    }
  }, [location.pathname, location.search, names, navigate]);

  return tokens;
}