import { NextResponse } from 'next/server';
import fs from 'fs/promises';
import path from 'path';

const FILE_PATH = path.join(process.cwd(), 'queries.json');

export async function GET() {
  try {
    let data = '[]';
    try {
      data = await fs.readFile(FILE_PATH, 'utf-8');
    } catch (e) {
      // File doesn't exist yet, return empty list
    }
    const queries = JSON.parse(data);
    return NextResponse.json(queries);
  } catch (error) {
    console.error('Failed to get queries:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}

export async function POST(req: Request) {
  try {
    const body = await req.json();
    const { user_id, query, response, timestamp } = body;

    let data = '[]';
    try {
      data = await fs.readFile(FILE_PATH, 'utf-8');
    } catch (e) {
      // File doesn't exist yet
    }
    const queries = JSON.parse(data);

    queries.push({
      user_id: user_id || 'unknown',
      query: query || '',
      response: response || '',
      timestamp: timestamp || new Date().toISOString(),
    });

    // Limit to latest 100 queries to prevent unbounded file growth
    const trimmedQueries = queries.slice(-100);

    await fs.writeFile(FILE_PATH, JSON.stringify(trimmedQueries, null, 2), 'utf-8');
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to save query:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}

export async function DELETE(req: Request) {
  try {
    const url = new URL(req.url);
    const timestamp = url.searchParams.get('timestamp');

    if (!timestamp) {
      return new NextResponse('Bad Request: Missing timestamp', { status: 400 });
    }

    let data = '[]';
    try {
      data = await fs.readFile(FILE_PATH, 'utf-8');
    } catch (e) {
      // File doesn't exist
    }
    let queries = JSON.parse(data);

    // Filter out the item matching the timestamp
    queries = queries.filter((q: any) => q.timestamp !== timestamp);

    await fs.writeFile(FILE_PATH, JSON.stringify(queries, null, 2), 'utf-8');
    return NextResponse.json({ success: true });
  } catch (error) {
    console.error('Failed to delete query:', error);
    return new NextResponse('Internal Server Error', { status: 500 });
  }
}
