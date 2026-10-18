/** Draws the element at the place `was` and moves it to the place it is at now. */
function glideFrom(element: HTMLElement, was: DOMRect, duration = 250) {
	const last = element.getBoundingClientRect();
	if (was.left === last.left && was.top === last.top && was.width === last.width) return;
	element.animate(
		[
			{
				transformOrigin: 'top left',
				transform: `translate(${was.left - last.left}px, ${was.top - last.top}px) scale(${was.width / last.width})`
			},
			{ transformOrigin: 'top left', transform: 'none' }
		],
		{ duration, easing: 'ease-out' }
	);
}

/**
 * Runs `change`, which changes the page and waits until it is drawn, and moves every element from the place it was
 * in to the place it is in now. The elements are put in their new places at once; each one is drawn at its old place
 * and moved to the new one, so nothing is measured while it moves. The page must not move them by other means. An
 * element that is not in the page any more is left alone.
 */
export async function glide(
	elements: (HTMLElement | null | undefined)[],
	change: () => Promise<void>,
	duration = 250
) {
	const moving = elements.filter((element) => element != null);
	const first = moving.map((element) => element.getBoundingClientRect());
	await change();
	moving.forEach((element, i) => {
		if (element.isConnected) glideFrom(element, first[i], duration);
	});
}
