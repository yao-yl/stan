#ifndef STAN_SERVICES_OPTIMIZE_NEWTON_HPP
#define STAN_SERVICES_OPTIMIZE_NEWTON_HPP

#include <stan/io/var_context.hpp>
#include <stan/io/chained_var_context.hpp>
#include <stan/io/random_var_context.hpp>
#include <stan/callbacks/writer.hpp>
#include <stan/optimization/newton.hpp>
#include <stan/services/error_codes.hpp>
#include <stan/model/util.hpp>
#include <stan/services/util/initialize.hpp>
#include <stan/services/util/rng.hpp>
#include <cmath>
#include <limits>
#include <string>
#include <vector>

namespace stan {
  namespace services {
    namespace optimize {

      /**
       * Runs the Newton algorithm for a model.
       *
       * @tparam Model A model implementation
       * @tparam Interrupt callback for interrupts
       *
       * @param[in] model the Stan model instantiated with data
       * @param init var context for initialization
       * @param random_seed random seed for the pseudo random number generator
       * @param chain chain id to advance the pseudo random number generator
       * @param init_radius radius to initialize
       * @param[in] num_iterations maximum number of iterations
       * @param[in] save_iterations indicates whether all the interations should
       *   be saved
       * @param[out] interrupt interrupt callback to be called every iteration
       * @param[out] message_writer output for messages
       * @param[out] init_writer Writer callback for unconstrained inits
       * @param[out] parameter_writer output for parameter values
       * @return stan::services::error_codes::OK (0) if successful
       */
      template <class Model, typename Interrupt>
      int newton(Model& model,
                 stan::io::var_context& init,
                 unsigned int random_seed,
                 unsigned int chain,
                 double init_radius,
                 int num_iterations,
                 bool save_iterations,
                 Interrupt& interrupt,
                 callbacks::writer& message_writer,
                 callbacks::writer& init_writer,
                 callbacks::writer& parameter_writer) {
        boost::ecuyer1988 rng = stan::services::util::rng(random_seed, chain);

        std::vector<int> disc_vector;
        std::vector<double> cont_vector
          = stan::services::util::initialize(model, init, rng, init_radius,
                                             false,
                                             message_writer, init_writer);

        std::stringstream message;

        double lp(0);
        try {
          lp = model.template log_prob<false, false>(cont_vector, disc_vector,
                                                     &message);
          message_writer(message.str());
        } catch (const std::exception& e) {
          message_writer();
          message_writer("Informational Message: The current Metropolis"
                         " proposal is about to be rejected because of"
                         " the following issue:");
          message_writer(e.what());
          message_writer("If this warning occurs sporadically, such as"
                         " for highly constrained variable types like"
                         " covariance matrices, then the sampler is fine,");
          message_writer("but if this warning occurs often then your model"
                         " may be either severely ill-conditioned or"
                         " misspecified.");
          lp = -std::numeric_limits<double>::infinity();
        }

        message.str("");
        message << "Initial log joint probability = " << lp;
        message_writer(message.str());

        std::vector<std::string> names;
        names.push_back("lp__");
        model.constrained_param_names(names, true, true);
        parameter_writer(names);

        double lastlp = lp;
        for (int m = 0; m < num_iterations; m++) {
          if (save_iterations) {
            std::vector<double> values;
            std::stringstream ss;
            model.write_array(rng, cont_vector, disc_vector, values,
                              true, true, &ss);
            if (ss.str().length() > 0)
              message_writer(ss.str());
            values.insert(values.begin(), lp);
            parameter_writer(values);
          }
          interrupt();
          lastlp = lp;
          lp = stan::optimization::newton_step(model, cont_vector, disc_vector);

          message.str("");
          message << "Iteration "
                  << std::setw(2) << (m + 1) << ". "
                  << "Log joint probability = " << std::setw(10) << lp
                  << ". Improved by " << (lp - lastlp) << ".";
          message_writer(message.str());

          if (std::fabs(lp - lastlp) <= 1e-8)
            break;
        }

        {
          std::vector<double> values;
          std::stringstream ss;
          model.write_array(rng, cont_vector, disc_vector, values,
                            true, true, &ss);
          if (ss.str().length() > 0)
            message_writer(ss.str());
          values.insert(values.begin(), lp);
          parameter_writer(values);
        }
        return stan::services::error_codes::OK;
      }

    }
  }
}
#endif
