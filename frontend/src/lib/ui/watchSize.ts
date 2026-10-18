/**
 * `watchWidth` and `watchHeight` report the width or the height of an element whenever it changes, but a frame
 * later. A report made at once can change the size of something observed in the same frame, and the browser then
 * answers with the error "ResizeObserver loop completed with undelivered notifications" (what `bind:clientWidth`
 * does).
 */
function watch(node: HTMLElement, read: () => void) {
	let frame = 0;
	const observer = new ResizeObserver(() => {
		cancelAnimationFrame(frame);
		frame = requestAnimationFrame(read);
	});
	observer.observe(node);
	return {
		destroy() {
			observer.disconnect();
			cancelAnimationFrame(frame);
		}
	};
}

export const watchWidth = (node: HTMLElement, report: (width: number) => void) =>
	watch(node, () => report(node.clientWidth));

export const watchHeight = (node: HTMLElement, report: (height: number) => void) =>
	watch(node, () => report(node.offsetHeight));
