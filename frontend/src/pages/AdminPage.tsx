import { Cpu, FileStack, Gauge, ShieldCheck, Users } from "lucide-react";

import { PageHeader } from "@/components/common/PageHeader";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { AccessPanel } from "@/features/admin/AccessPanel";
import { ActivityPanel } from "@/features/admin/ActivityPanel";
import { ConfigurationPanel } from "@/features/admin/ConfigurationPanel";
import { GovernancePanel } from "@/features/admin/GovernancePanel";
import { OverviewPanel } from "@/features/admin/OverviewPanel";
import { QualityPanel } from "@/features/admin/QualityPanel";

export function AdminPage() {
  return (
    <div className="space-y-5">
      <PageHeader
        title="Administration"
        description="Document governance, accounts and access, search and answer quality, activity, and the models this deployment actually runs. This area is limited to administrator accounts."
      />

      <Tabs defaultValue="overview">
        <TabsList className="flex-wrap">
          <TabsTrigger value="overview">
            <Gauge className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Overview
          </TabsTrigger>
          <TabsTrigger value="governance">
            <FileStack className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Documents &amp; governance
          </TabsTrigger>
          <TabsTrigger value="access">
            <Users className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Users &amp; access
          </TabsTrigger>
          <TabsTrigger value="quality">
            <ShieldCheck className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            Search &amp; answer quality
          </TabsTrigger>
          <TabsTrigger value="activity">Activity</TabsTrigger>
          <TabsTrigger value="configuration">
            <Cpu className="mr-1.5 h-3.5 w-3.5" aria-hidden="true" />
            System health &amp; configuration
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="space-y-4">
          <OverviewPanel />
        </TabsContent>
        <TabsContent value="governance" className="space-y-4">
          <GovernancePanel />
        </TabsContent>
        <TabsContent value="access" className="space-y-4">
          <AccessPanel />
        </TabsContent>
        <TabsContent value="quality" className="space-y-4">
          <QualityPanel />
        </TabsContent>
        <TabsContent value="activity">
          <ActivityPanel />
        </TabsContent>
        <TabsContent value="configuration" className="space-y-4">
          <ConfigurationPanel />
        </TabsContent>
      </Tabs>
    </div>
  );
}
