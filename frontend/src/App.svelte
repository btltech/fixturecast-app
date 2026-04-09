<script>
  import { Router } from "svelte-routing";
  import AppContent from "./components/AppContent.svelte";

  export let url = "";
</script>

<Router {url}>
  <AppContent />
</Router>
