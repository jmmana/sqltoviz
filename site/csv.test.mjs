import {test} from 'node:test';import assert from 'node:assert/strict';import {parseCsv} from './csv.mjs';
test('CRLF, BOM, numeric and null',()=>assert.deepEqual(parseCsv('\uFEFFa,v\r\nA,2\r\nB,\r\n'),[{a:'A',v:2},{a:'B',v:null}]));
test('quotes and multiline',()=>assert.deepEqual(parseCsv('a,v\n"a,b","x""y\nz"'),[{a:'a,b',v:'x"y\nz'}]));
test('preserve identifiers',()=>assert.deepEqual(parseCsv('id,v\n001,9007199254740993'),[{id:'001',v:'9007199254740993'}]));
test('invalid CSV',()=>{for(const x of ['a,a\n1,2','a,b\n1','a\n"x','a\n"x"y','a\n1"2','a'])assert.throws(()=>parseCsv(x));});
test('prototype-like keys',()=>assert.equal(Object.hasOwn(parseCsv('__proto__,v\nx,1')[0],'__proto__'),true));
test('row bound',()=>assert.throws(()=>parseCsv('a\n'+'1\n'.repeat(5001))));
