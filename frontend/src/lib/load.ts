import { error } from '@sveltejs/kit';

type Answer<T> = Promise<{ data?: T; response: Response }>;

/** The data of a detail page. A missing entity and a backend that is down become the error page. */
export async function loaded<T>(noun: string, request: Answer<T>): Promise<T> {
	let answer;
	try {
		answer = await request;
	} catch {
		error(502, `The ${noun} did not load. Is the backend running?`);
	}
	if (answer.data) return answer.data;
	if (answer.response.status === 404) error(404, `There is no such ${noun}.`);
	error(502, `The ${noun} did not load.`);
}
