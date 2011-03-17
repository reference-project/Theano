
import numpy
import theano
from theano import tensor, shared, function
import multinomial
from theano.compile.mode import get_default_mode, predefined_linkers

def run_with_c(f):
    mode = get_default_mode()
    linker_orig = mode.linker
    if linker_orig == predefined_linkers['py']:
        mode.linker = predefined_linkers['c|py']
    try:
        f(mode)
    finally:
        mode.linker = linker_orig


def test_multimomial_0():
    # This tests the multinomial Op directly, not going through the
    # multinomial() call in GPU random generation.

    p = tensor.matrix()
    u = tensor.vector()

    m = multinomial.Multinomial('auto')(p,u)

    def body(mode):
        #the m*2 allows the multinomial to reuse output
        f = function([p,u], m*2, allow_input_downcast=True, mode=mode)


        # test that both first and second samples can be drawn
        assert numpy.allclose(f([[1,0], [0,1]], [.1, .1]),
                [[2,0], [0,2]])

        # test that both second labels can be drawn
        r = f([[.2,.8], [.3,.7]], [.31, .31])
        assert numpy.allclose(r, [[0,2], [0,2]]), r


        # test that both first labels can be drawn
        r = f([[.2,.8], [.3,.7]], [.21, .21])
        assert numpy.allclose(r, [[0,2], [2,0]]), r

        #change the size to make sure output gets reallocated ok
        # and also make sure that the GPU version doesn't screw up the
        # transposed-ness
        r = f([[.2,.8] ], [.25])
        assert numpy.allclose(r, [[0,2]]), r

    run_with_c(body)


#TODO: check a bigger example (make sure blocking on GPU is handled correctly)
def test_multinomial_large():
    # DEBUG_MODE will test this on GPU
    def body(mode):
        p = tensor.fmatrix()
        u = tensor.fvector()
        m = multinomial.Multinomial('auto')(p,u)
        f = function([p,u], m*2, allow_input_downcast=True, mode=mode)

        pval = numpy.arange(10000 * 4, dtype='float32').reshape((10000, 4))+0.1
        pval = pval / pval.sum(axis=1)[:,None]
        uval = numpy.ones_like(pval[:,0]) * 0.5
        mval = f(pval,uval)

        assert mval.shape == pval.shape
        assert mval.dtype == pval.dtype
        assert numpy.allclose(mval.sum(axis=1), 2)
        asdf = numpy.asarray([0, 0, 2, 0])+0*pval
        assert numpy.allclose(mval, asdf) #broadcast over all rows
    run_with_c(body)


def test_multinomial_dtypes():
    p = tensor.dmatrix()
    u = tensor.dvector()
    m = multinomial.Multinomial('auto')(p,u)
    assert m.dtype == 'float64', m.dtype

    p = tensor.fmatrix()
    u = tensor.fvector()
    m = multinomial.Multinomial('auto')(p,u)
    assert m.dtype == 'float32', m.dtype


    p = tensor.fmatrix()
    u = tensor.fvector()
    m = multinomial.Multinomial('float64')(p,u)
    assert m.dtype == 'float64', m.dtype