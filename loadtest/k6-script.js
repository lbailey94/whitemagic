/**
 * k6 Load Testing Script for WhiteMagic API
 * 
 * Tests:
 * - Standard API endpoints
 * - Rust-powered performance endpoints
 * - Authentication
 * - Rate limiting
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// Custom metrics
const errorRate = new Rate('errors');
const rustPerformance = new Trend('rust_performance_ms');

// Test configuration
export const options = {
  stages: [
    { duration: '30s', target: 20 },   // Ramp up to 20 users
    { duration: '1m', target: 50 },    // Ramp up to 50 users
    { duration: '2m', target: 100 },   // Ramp up to 100 users
    { duration: '2m', target: 100 },   // Stay at 100 users
    { duration: '1m', target: 0 },     // Ramp down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'],  // 95% of requests < 500ms
    http_req_failed: ['rate<0.01'],    // Error rate < 1%
    errors: ['rate<0.05'],              // Custom error rate < 5%
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8000';
const API_KEY = __ENV.API_KEY || '';

export default function() {
  const headers = {
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY,
  };

  // Test 1: Health check
  {
    const res = http.get(`${BASE_URL}/health`);
    check(res, {
      'health check status 200': (r) => r.status === 200,
    }) || errorRate.add(1);
  }

  // Test 2: Performance status
  {
    const res = http.get(`${BASE_URL}/performance/status`, { headers });
    check(res, {
      'performance status 200': (r) => r.status === 200,
      'rust available check': (r) => {
        const body = JSON.parse(r.body);
        return body.rust_available !== undefined;
      },
    }) || errorRate.add(1);
  }

  // Test 3: Fast audit (Rust-powered)
  {
    const payload = JSON.stringify({
      directory: 'docs/plans',
      pattern: '*.md',
      max_files: 50,
    });

    const res = http.post(`${BASE_URL}/performance/audit`, payload, { headers });
    const success = check(res, {
      'audit status 200': (r) => r.status === 200,
      'audit processes files': (r) => {
        if (r.status === 200) {
          const body = JSON.parse(r.body);
          return body.statistics && body.statistics.total_files > 0;
        }
        return false;
      },
    });

    if (success && res.status === 200) {
      const body = JSON.parse(res.body);
      const duration = body.performance.duration_seconds * 1000; // Convert to ms
      rustPerformance.add(duration);
    } else {
      errorRate.add(1);
    }
  }

  // Test 4: Similarity calculation
  {
    const payload = JSON.stringify({
      text1: 'machine learning artificial intelligence',
      text2: 'machine learning deep learning',
      use_rust: true,
    });

    const res = http.post(`${BASE_URL}/performance/similarity`, payload, { headers });
    check(res, {
      'similarity status 200': (r) => r.status === 200,
      'similarity returns score': (r) => {
        if (r.status === 200) {
          const body = JSON.parse(r.body);
          return body.similarity >= 0 && body.similarity <= 1;
        }
        return false;
      },
    }) || errorRate.add(1);
  }

  // Test 5: Rate limit test (should occasionally hit limits)
  if (Math.random() < 0.1) {
    for (let i = 0; i < 15; i++) {
      const res = http.get(`${BASE_URL}/performance/status`, { headers });
      if (res.status === 429) {
        // Rate limit hit (expected)
        break;
      }
    }
  }

  sleep(1); // Pause between iterations
}

export function handleSummary(data) {
  return {
    'stdout': textSummary(data, { indent: ' ', enableColors: true }),
    'loadtest-results.json': JSON.stringify(data),
  };
}

function textSummary(data, options) {
  const indent = options.indent || '';
  const enableColors = options.enableColors || false;
  
  return `
${indent}✅ Load Test Summary
${indent}==================
${indent}
${indent}Total Requests: ${data.metrics.http_reqs.values.count}
${indent}Failed Requests: ${data.metrics.http_req_failed.values.rate * 100}%
${indent}
${indent}Response Times:
${indent}  avg: ${data.metrics.http_req_duration.values.avg.toFixed(2)}ms
${indent}  p95: ${data.metrics.http_req_duration.values['p(95)'].toFixed(2)}ms
${indent}  max: ${data.metrics.http_req_duration.values.max.toFixed(2)}ms
${indent}
${indent}Rust Performance:
${indent}  avg: ${data.metrics.rust_performance_ms ? data.metrics.rust_performance_ms.values.avg.toFixed(2) + 'ms' : 'N/A'}
${indent}
${indent}Throughput: ${data.metrics.http_reqs.values.rate.toFixed(2)} req/s
  `;
}
