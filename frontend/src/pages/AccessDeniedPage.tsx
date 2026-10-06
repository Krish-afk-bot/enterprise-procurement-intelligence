import { Link } from "react-router-dom";
import { Lock } from "lucide-react";

import { Button } from "@/components/ui/button";
import { PageHeader } from "@/components/common/PageHeader";
import { titleCase } from "@/lib/utils";
import { useAuth } from "@/store/auth";

export function AccessDeniedPage({ permission }: { permission: string }) {
  const user = useAuth((state) => state.user);

  return (
    <div className="space-y-5">
      <PageHeader title="This page is not available to your role" description="The API enforces the same check." />
      <div className="max-w-2xl rounded-lg border border-warning/35 bg-warning/5 p-4">
        <p className="flex items-center gap-2 text-sm font-medium">
          <Lock className="h-4 w-4 text-warning" aria-hidden="true" />
          Missing permission: <span className="font-mono text-xs">{permission}</span>
        </p>
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
          Your account holds the role <span className="font-medium text-foreground">{titleCase(user?.role)}</span> with{" "}
          {user?.permissions?.length ?? 0} permission(s). The interface hides this page, and the API would reject the
          request even if it were reachable, so nothing here depends on the browser check alone.
        </p>
        <p className="mt-2 text-xs leading-relaxed text-muted-foreground">
          An administrator can grant the permission by changing the role of this account.
        </p>
        <Button variant="outline" size="sm" className="mt-3" asChild>
          <Link to="/ask">Back to Ask</Link>
        </Button>
      </div>
    </div>
  );
}
