<script lang="ts">
	let { value, label = `#${value}` }: { value: number | string; label?: string } = $props();

	let copied = $state(false);

	async function copy() {
		try {
			await navigator.clipboard.writeText(String(value));
		} catch {
			return; // no clipboard in this context: nothing to confirm
		}
		copied = true;
		setTimeout(() => (copied = false), 1200);
	}
</script>

<button
	type="button"
	title="Copy the Genius id"
	class="font-mono text-xs {copied
		? 'text-success'
		: 'text-surface-content/40 hover:text-surface-content'}"
	onclick={copy}
>
	{copied ? 'copied' : label}
</button>
