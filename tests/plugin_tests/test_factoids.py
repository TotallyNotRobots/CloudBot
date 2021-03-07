import itertools
import string
from unittest.mock import MagicMock, call

from plugins import factoids


def test_forget(mock_db, patch_paste):
    patch_paste.return_value = "PASTEURL"
    factoids.table.create(mock_db.engine)
    chan = "#example"
    mock_db.add_row(
        factoids.table,
        chan=chan,
        word="foo",
        nick="bar",
        data="things",
    )
    factoids.load_cache(mock_db.session())

    assert mock_db.get_data(factoids.table) == [
        ("foo", "things", "bar", "#example")
    ]

    event = MagicMock()
    factoids.forget("foo bar", chan, mock_db.session(), event.notice)
    assert event.mock_calls == [
        call.notice("Unknown factoids: 'bar'"),
        call.notice("Removed Data: PASTEURL"),
    ]

    assert mock_db.get_data(factoids.table) == []


def test_remove_fact_no_paste(mock_requests, mock_db):
    factoids.table.create(mock_db.engine)
    factoids.load_cache(mock_db.session())
    event = MagicMock()
    chan = "#example"

    factoids.remove_fact("#example", ["foo"], mock_db.session(), event.notice)
    assert event.mock_calls == [call.notice("Unknown factoids: 'foo'")]

    event.reset_mock()

    mock_db.add_row(
        factoids.table,
        chan=chan,
        word="foo",
        nick="bar",
        data="things",
    )
    factoids.load_cache(mock_db.session())

    factoids.remove_fact(
        "#example", ["foo", "bar"], mock_db.session(), event.notice
    )
    assert event.mock_calls == [
        call.notice("Unknown factoids: 'bar'"),
        call.notice("Unable to paste removed data, not removing facts"),
    ]


def test_remove_fact(patch_paste, mock_db):
    factoids.table.create(mock_db.engine)
    factoids.load_cache(mock_db.session())
    event = MagicMock()
    assert mock_db.get_data(factoids.table) == []

    factoids.remove_fact("#example", ["foo"], mock_db.session(), event.notice)
    assert event.mock_calls == [call.notice("Unknown factoids: 'foo'")]

    mock_db.add_row(
        factoids.table,
        chan="#example",
        word="foo",
        nick="bar",
        data="things",
    )

    factoids.load_cache(mock_db.session())
    assert mock_db.get_data(factoids.table) == [
        ("foo", "things", "bar", "#example")
    ]

    patch_paste.return_value = "PASTEURL"
    event.reset_mock()
    factoids.remove_fact("#example", ["foo"], mock_db.session(), event.notice)
    assert event.mock_calls == [call.notice("Removed Data: PASTEURL")]
    patch_paste.assert_called_with(
        b"| Command | Output |\n| ------- | ------ |\n| ?foo    | things |",
        "md",
        "hastebin",
        raise_on_no_paste=True,
    )

    assert mock_db.get_data(factoids.table) == []


def test_clear_facts(mock_db):
    factoids.table.create(mock_db.engine)
    mock_db.add_row(
        factoids.table, word="foo", data="bar", nick="user", chan="#example"
    )

    mock_db.add_row(
        factoids.table, word="foo1", data="bar", nick="user", chan="#example"
    )

    factoids.load_cache(mock_db.session())

    assert mock_db.get_data(factoids.table) == [
        ("foo", "bar", "user", "#example"),
        ("foo1", "bar", "user", "#example"),
    ]

    assert (
        factoids.forget_all("#example", mock_db.session()) == "Facts cleared."
    )

    assert mock_db.get_data(factoids.table) == []


def test_list_facts(mock_db):
    factoids.table.create(mock_db.engine)
    factoids.load_cache(mock_db.session())
    event = MagicMock()

    names = [
        "".join(c) for c in itertools.product(string.ascii_lowercase, repeat=2)
    ]

    for name in names:
        factoids.add_factoid(
            mock_db.session(),
            name.lower(),
            "#chan",
            name,
            "nick",
        )

    factoids.listfactoids(event.notice, "#chan")

    assert event.mock_calls == [
        call.notice(
            "?aa, ?ab, ?ac, ?ad, ?ae, ?af, ?ag, ?ah, ?ai, ?aj, ?ak, ?al, ?am, ?an, ?ao, ?ap, ?aq, ?ar, ?as, ?at, ?au, ?av, ?aw, ?ax, ?ay, ?az, ?ba, ?bb, ?bc, ?bd, ?be, ?bf, ?bg, ?bh, ?bi, ?bj, ?bk, ?bl, ?bm, ?bn, ?bo, ?bp, ?bq, ?br, ?bs, ?bt, ?bu, ?bv, ?bw, ?bx, ?by, ?bz, ?ca, ?cb, ?cc, ?cd, ?ce, ?cf, ?cg, ?ch, ?ci, ?cj, ?ck, ?cl, ?cm, ?cn, ?co, ?commands, ?cp, ?cq, ?cr, ?cs, ?ct, ?cu, ?cv, ?cw, ?cx, ?cy"
        ),
        call.notice(
            "?cz, ?da, ?db, ?dc, ?dd, ?de, ?df, ?dg, ?dh, ?di, ?dj, ?dk, ?dl, ?dm, ?dn, ?do, ?dp, ?dq, ?dr, ?ds, ?dt, ?du, ?dv, ?dw, ?dx, ?dy, ?dz, ?ea, ?eb, ?ec, ?ed, ?ee, ?ef, ?eg, ?eh, ?ei, ?ej, ?ek, ?el, ?em, ?en, ?eo, ?ep, ?eq, ?er, ?es, ?et, ?eu, ?ev, ?ew, ?ex, ?ey, ?ez, ?fa, ?fb, ?fc, ?fd, ?fe, ?ff, ?fg, ?fh, ?fi, ?fj, ?fk, ?fl, ?fm, ?fn, ?fo, ?fp, ?fq, ?fr, ?fs, ?ft, ?fu, ?fv, ?fw, ?fx, ?fy, ?fz, ?ga"
        ),
        call.notice(
            "?gb, ?gc, ?gd, ?ge, ?gf, ?gg, ?gh, ?gi, ?gj, ?gk, ?gl, ?gm, ?gn, ?go, ?gp, ?gq, ?gr, ?gs, ?gt, ?gu, ?gv, ?gw, ?gx, ?gy, ?gz, ?ha, ?hb, ?hc, ?hd, ?he, ?hf, ?hg, ?hh, ?hi, ?hj, ?hk, ?hl, ?hm, ?hn, ?ho, ?hp, ?hq, ?hr, ?hs, ?ht, ?hu, ?hv, ?hw, ?hx, ?hy, ?hz, ?ia, ?ib, ?ic, ?id, ?ie, ?if, ?ig, ?ih, ?ii, ?ij, ?ik, ?il, ?im, ?in, ?io, ?ip, ?iq, ?ir, ?is, ?it, ?iu, ?iv, ?iw, ?ix, ?iy, ?iz, ?ja, ?jb, ?jc"
        ),
        call.notice(
            "?jd, ?je, ?jf, ?jg, ?jh, ?ji, ?jj, ?jk, ?jl, ?jm, ?jn, ?jo, ?jp, ?jq, ?jr, ?js, ?jt, ?ju, ?jv, ?jw, ?jx, ?jy, ?jz, ?ka, ?kb, ?kc, ?kd, ?ke, ?kf, ?kg, ?kh, ?ki, ?kj, ?kk, ?kl, ?km, ?kn, ?ko, ?kp, ?kq, ?kr, ?ks, ?kt, ?ku, ?kv, ?kw, ?kx, ?ky, ?kz, ?la, ?lb, ?lc, ?ld, ?le, ?lf, ?lg, ?lh, ?li, ?lj, ?lk, ?ll, ?lm, ?ln, ?lo, ?lp, ?lq, ?lr, ?ls, ?lt, ?lu, ?lv, ?lw, ?lx, ?ly, ?lz, ?ma, ?mb, ?mc, ?md, ?me"
        ),
        call.notice(
            "?mf, ?mg, ?mh, ?mi, ?mj, ?mk, ?ml, ?mm, ?mn, ?mo, ?mp, ?mq, ?mr, ?ms, ?mt, ?mu, ?mv, ?mw, ?mx, ?my, ?mz, ?na, ?nb, ?nc, ?nd, ?ne, ?nf, ?ng, ?nh, ?ni, ?nj, ?nk, ?nl, ?nm, ?nn, ?no, ?np, ?nq, ?nr, ?ns, ?nt, ?nu, ?nv, ?nw, ?nx, ?ny, ?nz, ?oa, ?ob, ?oc, ?od, ?oe, ?of, ?og, ?oh, ?oi, ?oj, ?ok, ?ol, ?om, ?on, ?oo, ?op, ?oq, ?or, ?os, ?ot, ?ou, ?ov, ?ow, ?ox, ?oy, ?oz, ?pa, ?pb, ?pc, ?pd, ?pe, ?pf, ?pg"
        ),
        call.notice(
            "?ph, ?pi, ?pj, ?pk, ?pl, ?pm, ?pn, ?po, ?pp, ?pq, ?pr, ?ps, ?pt, ?pu, ?pv, ?pw, ?px, ?py, ?pz, ?qa, ?qb, ?qc, ?qd, ?qe, ?qf, ?qg, ?qh, ?qi, ?qj, ?qk, ?ql, ?qm, ?qn, ?qo, ?qp, ?qq, ?qr, ?qs, ?qt, ?qu, ?qv, ?qw, ?qx, ?qy, ?qz, ?ra, ?rb, ?rc, ?rd, ?re, ?rf, ?rg, ?rh, ?ri, ?rj, ?rk, ?rl, ?rm, ?rn, ?ro, ?rp, ?rq, ?rr, ?rs, ?rt, ?ru, ?rv, ?rw, ?rx, ?ry, ?rz, ?sa, ?sb, ?sc, ?sd, ?se, ?sf, ?sg, ?sh, ?si"
        ),
        call.notice(
            "?sj, ?sk, ?sl, ?sm, ?sn, ?so, ?sp, ?sq, ?sr, ?ss, ?st, ?su, ?sv, ?sw, ?sx, ?sy, ?sz, ?ta, ?tb, ?tc, ?td, ?te, ?tf, ?tg, ?th, ?ti, ?tj, ?tk, ?tl, ?tm, ?tn, ?to, ?tp, ?tq, ?tr, ?ts, ?tt, ?tu, ?tv, ?tw, ?tx, ?ty, ?tz, ?ua, ?ub, ?uc, ?ud, ?ue, ?uf, ?ug, ?uh, ?ui, ?uj, ?uk, ?ul, ?um, ?un, ?uo, ?up, ?uq, ?ur, ?us, ?ut, ?uu, ?uv, ?uw, ?ux, ?uy, ?uz, ?va, ?vb, ?vc, ?vd, ?ve, ?vf, ?vg, ?vh, ?vi, ?vj, ?vk"
        ),
        call.notice(
            "?vl, ?vm, ?vn, ?vo, ?vp, ?vq, ?vr, ?vs, ?vt, ?vu, ?vv, ?vw, ?vx, ?vy, ?vz, ?wa, ?wb, ?wc, ?wd, ?we, ?wf, ?wg, ?wh, ?wi, ?wj, ?wk, ?wl, ?wm, ?wn, ?wo, ?wp, ?wq, ?wr, ?ws, ?wt, ?wu, ?wv, ?ww, ?wx, ?wy, ?wz, ?xa, ?xb, ?xc, ?xd, ?xe, ?xf, ?xg, ?xh, ?xi, ?xj, ?xk, ?xl, ?xm, ?xn, ?xo, ?xp, ?xq, ?xr, ?xs, ?xt, ?xu, ?xv, ?xw, ?xx, ?xy, ?xz, ?ya, ?yb, ?yc, ?yd, ?ye, ?yf, ?yg, ?yh, ?yi, ?yj, ?yk, ?yl, ?ym"
        ),
        call.notice(
            "?yn, ?yo, ?yp, ?yq, ?yr, ?ys, ?yt, ?yu, ?yv, ?yw, ?yx, ?yy, ?yz, ?za, ?zb, ?zc, ?zd, ?ze, ?zf, ?zg, ?zh, ?zi, ?zj, ?zk, ?zl, ?zm, ?zn, ?zo, ?zp, ?zq, ?zr, ?zs, ?zt, ?zu, ?zv, ?zw, ?zx, ?zy, ?zz"
        ),
    ]
