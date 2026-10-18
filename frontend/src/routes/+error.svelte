<script lang="ts">
	import { page } from '$app/state';
</script>

<p class="text-sm {page.status === 404 ? 'text-surface-content/60' : 'text-danger'}">
	{page.error?.message}
</p>
